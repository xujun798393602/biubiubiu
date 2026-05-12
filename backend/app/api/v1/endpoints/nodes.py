"""Node management endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.models.node import TestNode, NodeGroup
from app.models.user import User
from app.schemas.common import ResponseModel
from app.schemas.node import NodeCreate, NodeUpdate, NodeItem, GroupCreate

router = APIRouter()


@router.get("", response_model=ResponseModel)
async def list_nodes(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    status: str = Query(None),
    keyword: str = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(TestNode).where(TestNode.deleted_at.is_(None))
    count_query = select(func.count()).select_from(TestNode).where(TestNode.deleted_at.is_(None))

    if status:
        query = query.where(TestNode.status == status)
        count_query = count_query.where(TestNode.status == status)
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
async def create_node(body: NodeCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_roles("ADMIN", "OPS"))):
    # Check duplicate name
    existing = (await db.execute(select(TestNode).where(TestNode.name == body.name, TestNode.deleted_at.is_(None)))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail={"code": "NODE_DUPLICATE", "message": "节点名称已存在"})
    node = TestNode(**body.model_dump())
    db.add(node)
    await db.commit()
    return ResponseModel(data={"id": str(node.id)})


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
async def node_heartbeat(node_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TestNode).where(TestNode.id == node_id, TestNode.deleted_at.is_(None)))
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail={"code": "NODE_NOT_FOUND", "message": "节点不存在"})
    node.last_heartbeat_at = datetime.now(timezone.utc)
    node.status = "ONLINE"
    await db.commit()
    return ResponseModel(message="心跳更新成功")
