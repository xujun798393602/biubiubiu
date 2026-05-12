"""System management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.models.system import SystemLog, Notification, SystemConfig
from app.models.user import User
from app.schemas.common import ResponseModel
from app.schemas.system import SystemLogItem, NotificationItem, ConfigUpdate

router = APIRouter()


@router.get("/logs", response_model=ResponseModel)
async def list_logs(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    operation: str = Query(None),
    resource_type: str = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "OPS")),
):
    query = select(SystemLog).where(SystemLog.deleted_at.is_(None))
    count_query = select(func.count()).select_from(SystemLog).where(SystemLog.deleted_at.is_(None))
    if operation:
        query = query.where(SystemLog.operation == operation)
        count_query = count_query.where(SystemLog.operation == operation)
    if resource_type:
        query = query.where(SystemLog.resource_type == resource_type)
        count_query = count_query.where(SystemLog.resource_type == resource_type)

    total = (await db.execute(count_query)).scalar()
    items = (await db.execute(query.order_by(SystemLog.created_at.desc()).offset((page - 1) * pageSize).limit(pageSize))).scalars().all()

    return ResponseModel(data={
        "list": [SystemLogItem.model_validate(i) for i in items],
        "pagination": {"page": page, "pageSize": pageSize, "total": total, "totalPages": (total + pageSize - 1) // pageSize},
    })


@router.get("/notifications", response_model=ResponseModel)
async def list_notifications(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Notification).where(Notification.user_id == current_user.id, Notification.deleted_at.is_(None))
    total = (await db.execute(select(func.count()).select_from(Notification).where(Notification.user_id == current_user.id, Notification.deleted_at.is_(None)))).scalar()
    items = (await db.execute(query.order_by(Notification.created_at.desc()).offset((page - 1) * pageSize).limit(pageSize))).scalars().all()

    return ResponseModel(data={
        "list": [NotificationItem.model_validate(i) for i in items],
        "pagination": {"page": page, "pageSize": pageSize, "total": total, "totalPages": (total + pageSize - 1) // pageSize},
    })


@router.put("/notifications/{notification_id}/read", response_model=ResponseModel)
async def mark_read(notification_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    from datetime import datetime, timezone
    result = await db.execute(select(Notification).where(Notification.id == notification_id, Notification.user_id == current_user.id))
    n = result.scalar_one_or_none()
    if not n:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "通知不存在"})
    n.is_read = True
    n.read_at = datetime.now(timezone.utc)
    await db.commit()
    return ResponseModel(message="已标记为已读")


@router.get("/config", response_model=ResponseModel)
async def get_config(db: AsyncSession = Depends(get_db), current_user: User = Depends(require_roles("ADMIN", "OPS"))):
    configs = (await db.execute(select(SystemConfig).where(SystemConfig.deleted_at.is_(None)))).scalars().all()
    return ResponseModel(data={c.key: c.value for c in configs})


@router.put("/config", response_model=ResponseModel)
async def update_config(body: ConfigUpdate, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_roles("ADMIN"))):
    result = await db.execute(select(SystemConfig).where(SystemConfig.key == body.key, SystemConfig.deleted_at.is_(None)))
    config = result.scalar_one_or_none()
    if config:
        config.value = str(body.value)
        if body.description:
            config.description = body.description
    else:
        db.add(SystemConfig(key=body.key, value=str(body.value), description=body.description))
    await db.commit()
    return ResponseModel(message="配置更新成功")


@router.get("/stats", response_model=ResponseModel)
async def get_stats(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.models.test_case import TestCase
    from app.models.task import Task
    from app.models.node import TestNode

    cases = (await db.execute(select(func.count()).select_from(TestCase).where(TestCase.deleted_at.is_(None)))).scalar()
    tasks = (await db.execute(select(func.count()).select_from(Task).where(Task.deleted_at.is_(None)))).scalar()
    nodes = (await db.execute(select(func.count()).select_from(TestNode).where(TestNode.deleted_at.is_(None)))).scalar()

    return ResponseModel(data={"totalCases": cases, "totalTasks": tasks, "totalNodes": nodes})
