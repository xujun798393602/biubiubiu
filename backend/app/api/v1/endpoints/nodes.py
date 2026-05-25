"""Node management endpoints."""

import hashlib
import secrets
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.models.node import TestNode, NodeGroup
from app.models.user import User
from app.models.enums import NodeStatus, NodeType
from app.schemas.common import ResponseModel
from app.schemas.node import (
    NodeCreate, NodeUpdate, NodeItem, GroupCreate,
    NodeAutoRegister, NodeStats, NodeScaleRequest, NodeScaleResponse,
)
from app.services.queue_manager import queue_manager

router = APIRouter()


def generate_api_key() -> str:
    """Generate a secure API key for node authentication."""
    return secrets.token_hex(32)


@router.get("", response_model=ResponseModel)
async def list_nodes(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    node_type: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(TestNode).where(TestNode.deleted_at.is_(None))
    count_query = select(func.count()).select_from(TestNode).where(TestNode.deleted_at.is_(None))

    if status:
        query = query.where(TestNode.status == status)
        count_query = count_query.where(TestNode.status == status)
    if node_type:
        query = query.where(TestNode.node_type == node_type)
        count_query = count_query.where(TestNode.node_type == node_type)
    if keyword:
        query = query.where(TestNode.name.ilike(f"%{keyword}%"))
        count_query = count_query.where(TestNode.name.ilike(f"%{keyword}%"))

    total = (await db.execute(count_query)).scalar()
    items = (await db.execute(query.offset((page - 1) * pageSize).limit(pageSize))).scalars().all()

    return ResponseModel(data={
        "list": [NodeItem.model_validate(i) for i in items],
        "pagination": {"page": page, "pageSize": pageSize, "total": total, "totalPages": (total + pageSize - 1) // pageSize},
    })


@router.post("", response_model=ResponseModel, status_code=201)
async def create_node(
    body: NodeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "OPS")),
):
    """Manually register a new node."""
    # Check duplicate name
    existing = (await db.execute(
        select(TestNode).where(TestNode.name == body.name, TestNode.deleted_at.is_(None))
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail={"code": "NODE_DUPLICATE", "message": "节点名称已存在"})

    # Generate API key
    api_key = generate_api_key()

    node = TestNode(
        name=body.name,
        host=body.host,
        port=body.port,
        node_type=NodeType(body.node_type) if body.node_type else NodeType.MIXED,
        group_id=body.group_id,
        max_concurrent=body.max_concurrent,
        capabilities=body.capabilities,
        api_key=api_key,
    )
    db.add(node)
    await db.commit()

    return ResponseModel(data={
        "id": str(node.id),
        "api_key": api_key,
        "message": "节点创建成功，请将 api_key 配置到 Worker 环境变量中",
    })


@router.post("/auto-register", response_model=ResponseModel, status_code=201)
async def auto_register_node(
    body: NodeAutoRegister,
    db: AsyncSession = Depends(get_db),
):
    """Auto-register a worker node (called by worker on startup)."""
    # Check if node already exists by name
    existing = (await db.execute(
        select(TestNode).where(TestNode.name == body.name, TestNode.deleted_at.is_(None))
    )).scalar_one_or_none()

    if existing:
        # Update existing node
        existing.host = body.host
        existing.port = body.port
        existing.node_type = NodeType(body.node_type) if body.node_type else NodeType.MIXED
        existing.capabilities = body.capabilities
        existing.agent_version = body.agent_version
        existing.status = NodeStatus.ONLINE
        existing.last_heartbeat_at = datetime.now(timezone.utc)
        await db.commit()

        return ResponseModel(data={
            "id": str(existing.id),
            "api_key": existing.api_key,
            "message": "节点已更新",
        })

    # Create new node
    api_key = generate_api_key()

    node = TestNode(
        name=body.name,
        host=body.host,
        port=body.port,
        node_type=NodeType(body.node_type) if body.node_type else NodeType.MIXED,
        capabilities=body.capabilities,
        agent_version=body.agent_version,
        api_key=api_key,
        status=NodeStatus.ONLINE,
        last_heartbeat_at=datetime.now(timezone.utc),
    )
    db.add(node)
    await db.commit()

    return ResponseModel(data={
        "id": str(node.id),
        "api_key": api_key,
        "message": "节点注册成功",
    })


@router.get("/stats", response_model=ResponseModel)
async def get_node_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get node statistics."""
    # Get total counts by status
    status_counts = {}
    for status in NodeStatus:
        count = (await db.execute(
            select(func.count()).select_from(TestNode).where(
                and_(TestNode.deleted_at.is_(None), TestNode.status == status)
            )
        )).scalar()
        status_counts[status.value] = count

    # Get counts by type
    type_counts = {}
    for node_type in NodeType:
        count = (await db.execute(
            select(func.count()).select_from(TestNode).where(
                and_(TestNode.deleted_at.is_(None), TestNode.node_type == node_type)
            )
        )).scalar()
        type_counts[node_type.value] = count

    # Get total tasks and capacity
    total_tasks = (await db.execute(
        select(func.sum(TestNode.current_tasks)).where(TestNode.deleted_at.is_(None))
    )).scalar() or 0

    total_capacity = (await db.execute(
        select(func.sum(TestNode.max_concurrent)).where(
            and_(TestNode.deleted_at.is_(None), TestNode.status == NodeStatus.ONLINE)
        )
    )).scalar() or 0

    # Get queue depths from Redis
    queue_depth = await queue_manager.get_queue_depth()

    stats = NodeStats(
        total_nodes=sum(status_counts.values()),
        online_nodes=status_counts.get("ONLINE", 0),
        offline_nodes=status_counts.get("OFFLINE", 0),
        busy_nodes=status_counts.get("BUSY", 0),
        error_nodes=status_counts.get("ERROR", 0),
        by_type=type_counts,
        total_tasks_running=total_tasks,
        total_max_concurrent=total_capacity,
    )

    return ResponseModel(data={
        **stats.model_dump(),
        "queue_depth": queue_depth,
    })


# ── Static routes MUST come before /{node_id} ──────────────────

@router.get("/groups", response_model=ResponseModel)
async def list_groups(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    groups = (await db.execute(select(NodeGroup).where(NodeGroup.deleted_at.is_(None)))).scalars().all()
    return ResponseModel(data=[{"id": str(g.id), "name": g.name} for g in groups])


@router.post("/groups", response_model=ResponseModel, status_code=201)
async def create_group(body: GroupCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_roles("ADMIN", "OPS"))):
    group = NodeGroup(name=body.name, description=body.description)
    db.add(group)
    await db.commit()
    return ResponseModel(data={"id": str(group.id)})


@router.post("/scale", response_model=ResponseModel)
async def scale_nodes(
    body: NodeScaleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "OPS")),
):
    """Scale up worker nodes (creates node records for manual or auto registration)."""
    created_nodes = []

    for i in range(body.count):
        # Generate unique name
        base_name = body.name
        name = f"{base_name}-{i + 1}"

        # Check if name exists
        existing = (await db.execute(
            select(TestNode).where(TestNode.name == name, TestNode.deleted_at.is_(None))
        )).scalar_one_or_none()

        if existing:
            # Try with timestamp suffix
            import time
            name = f"{base_name}-{int(time.time())}-{i}"

        api_key = generate_api_key()

        node = TestNode(
            name=name,
            host=body.host,
            port=body.port,
            node_type=NodeType(body.node_type) if body.node_type else NodeType.MIXED,
            group_id=body.group_id,
            max_concurrent=body.max_concurrent,
            capabilities=body.capabilities,
            api_key=api_key,
        )
        db.add(node)
        created_nodes.append({"name": name, "api_key": api_key})

    await db.commit()

    return ResponseModel(data=NodeScaleResponse(
        created_nodes=[n["name"] for n in created_nodes],
        message=f"已创建 {len(created_nodes)} 个节点",
    ).model_dump())


# ── Parameterized routes ───────────────────────────────────────

@router.get("/{node_id}", response_model=ResponseModel)
async def get_node(node_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(TestNode).where(TestNode.id == node_id, TestNode.deleted_at.is_(None)))
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail={"code": "NODE_NOT_FOUND", "message": "节点不存在"})
    return ResponseModel(data=NodeItem.model_validate(node))


@router.put("/{node_id}", response_model=ResponseModel)
async def update_node(node_id: str, body: NodeUpdate, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_roles("ADMIN", "OPS"))):
    result = await db.execute(select(TestNode).where(TestNode.id == node_id, TestNode.deleted_at.is_(None)))
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail={"code": "NODE_NOT_FOUND", "message": "节点不存在"})
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(node, k, v)
    await db.commit()
    return ResponseModel(message="更新成功")


@router.delete("/{node_id}", response_model=ResponseModel)
async def delete_node(node_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_roles("ADMIN"))):
    result = await db.execute(select(TestNode).where(TestNode.id == node_id, TestNode.deleted_at.is_(None)))
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail={"code": "NODE_NOT_FOUND", "message": "节点不存在"})
    node.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    return ResponseModel(message="删除成功")


@router.post("/{node_id}/heartbeat", response_model=ResponseModel)
async def node_heartbeat(
    node_id: str,
    metrics: Optional[dict] = None,
    db: AsyncSession = Depends(get_db),
):
    """Update node heartbeat and metrics."""
    result = await db.execute(select(TestNode).where(TestNode.id == node_id, TestNode.deleted_at.is_(None)))
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail={"code": "NODE_NOT_FOUND", "message": "节点不存在"})

    node.last_heartbeat_at = datetime.now(timezone.utc)
    node.status = NodeStatus.ONLINE

    # Update metrics if provided
    if metrics:
        node.cpu_usage = metrics.get("cpu_usage", node.cpu_usage)
        node.memory_usage = metrics.get("memory_usage", node.memory_usage)
        node.disk_usage = metrics.get("disk_usage", node.disk_usage)
        node.current_tasks = metrics.get("current_tasks", node.current_tasks)

    await db.commit()

    # Also update Redis heartbeat
    await queue_manager.update_node_heartbeat(node_id, metrics or {})

    return ResponseModel(message="心跳更新成功")


@router.post("/{node_id}/api-key", response_model=ResponseModel)
async def regenerate_api_key(
    node_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN")),
):
    """Regenerate API key for a node."""
    result = await db.execute(select(TestNode).where(TestNode.id == node_id, TestNode.deleted_at.is_(None)))
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail={"code": "NODE_NOT_FOUND", "message": "节点不存在"})

    node.api_key = generate_api_key()
    await db.commit()

    return ResponseModel(data={
        "api_key": node.api_key,
        "message": "API Key 已重新生成",
    })
