"""Task management endpoints."""

import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.task import Task, TaskLog
from app.models.test_case import TaskCase, TestCase
from app.models.user import User
from app.schemas.common import ResponseModel
from app.schemas.task import TaskCreate, TaskUpdate, TaskItem, TaskDetail, TaskCaseInfo

router = APIRouter()


@router.get("", response_model=ResponseModel)
async def list_tasks(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    status: str = Query(None),
    priority: str = Query(None),
    keyword: str = Query(None),
    creator_id: str = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Task, User.username).outerjoin(User, Task.creator_id == User.id).where(Task.deleted_at.is_(None))
    count_query = select(func.count()).select_from(Task).where(Task.deleted_at.is_(None))

    if status:
        query = query.where(Task.status == status)
        count_query = count_query.where(Task.status == status)
    if priority:
        query = query.where(Task.priority == priority)
        count_query = count_query.where(Task.priority == priority)
    if keyword:
        query = query.where(Task.name.ilike(f"%{keyword}%"))
        count_query = count_query.where(Task.name.ilike(f"%{keyword}%"))
    if creator_id:
        query = query.where(Task.creator_id == creator_id)
        count_query = count_query.where(Task.creator_id == creator_id)

    total = (await db.execute(count_query)).scalar()
    rows = (await db.execute(query.order_by(Task.created_at.desc()).offset((page - 1) * pageSize).limit(pageSize))).all()

    task_list = []
    for task, creator_name in rows:
        item = TaskItem.model_validate(task).model_dump()
        item["creator_name"] = creator_name or ""
        task_list.append(item)

    return ResponseModel(data={
        "list": task_list,
        "pagination": {"page": page, "pageSize": pageSize, "total": total, "totalPages": (total + pageSize - 1) // pageSize},
    })


@router.get("/creators", response_model=ResponseModel)
async def list_creators(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Return distinct creators for filter dropdown."""
    query = (
        select(User.id, User.username)
        .join(Task, Task.creator_id == User.id)
        .where(Task.deleted_at.is_(None), User.deleted_at.is_(None))
        .distinct()
        .order_by(User.username)
    )
    rows = (await db.execute(query)).all()
    return ResponseModel(data=[{"id": str(r.id), "username": r.username} for r in rows])


@router.post("", response_model=ResponseModel, status_code=201)
async def create_task(body: TaskCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Validate all case_ids exist
    if body.case_ids:
        existing = (await db.execute(
            select(TestCase.id).where(TestCase.id.in_(body.case_ids), TestCase.deleted_at.is_(None))
        )).scalars().all()
        if len(existing) != len(body.case_ids):
            raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "部分用例不存在"})

    task = Task(
        name=body.name,
        description=body.description,
        priority=body.priority,
        execute_type=body.execute_type,
        schedule_cron=body.schedule_cron,
        creator_id=current_user.id,
        total_cases=len(body.case_ids),
    )
    db.add(task)
    await db.flush()
    for i, case_id in enumerate(body.case_ids):
        db.add(TaskCase(task_id=task.id, case_id=case_id, sort_order=i))
    await db.commit()
    return ResponseModel(data={"id": str(task.id)})


@router.get("/{task_id}", response_model=ResponseModel)
async def get_task(task_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(
        select(Task, User.username).outerjoin(User, Task.creator_id == User.id)
        .where(Task.id == task_id, Task.deleted_at.is_(None))
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail={"code": "TASK_NOT_FOUND", "message": "任务不存在"})
    task, creator_name = row

    # Fetch associated cases via join
    cases_query = (
        select(TaskCase, TestCase)
        .join(TestCase, TaskCase.case_id == TestCase.id)
        .where(TaskCase.task_id == task.id, TaskCase.deleted_at.is_(None))
        .order_by(TaskCase.sort_order)
    )
    cases_result = await db.execute(cases_query)
    cases = [
        TaskCaseInfo(
            case_id=str(tc.case_id),
            case_name=tc_model.name,
            case_type=tc_model.type,
            sort_order=tc.sort_order,
        )
        for tc, tc_model in cases_result.all()
    ]

    task_data = TaskItem.model_validate(task).model_dump()
    task_data["creator_name"] = creator_name or ""
    task_data["schedule_cron"] = task.schedule_cron
    task_data["cases"] = [c.model_dump() for c in cases]
    return ResponseModel(data=task_data)


@router.put("/{task_id}", response_model=ResponseModel)
async def update_task(task_id: str, body: TaskUpdate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Task).where(Task.id == task_id, Task.deleted_at.is_(None)))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail={"code": "TASK_NOT_FOUND", "message": "任务不存在"})
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(task, k, v)
    await db.commit()
    return ResponseModel(message="更新成功")


@router.delete("/{task_id}", response_model=ResponseModel)
async def delete_task(task_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Task).where(Task.id == task_id, Task.deleted_at.is_(None)))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail={"code": "TASK_NOT_FOUND", "message": "任务不存在"})
    task.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    return ResponseModel(message="删除成功")


@router.post("/{task_id}/start", response_model=ResponseModel)
async def start_task(task_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Task).where(Task.id == task_id, Task.deleted_at.is_(None)))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail={"code": "TASK_NOT_FOUND", "message": "任务不存在"})
    if task.status not in ("PENDING", "SCHEDULED"):
        raise HTTPException(status_code=400, detail={"code": "INVALID_STATUS", "message": f"任务状态为 {task.status}，无法启动"})
    task.status = "RUNNING"
    task.started_at = datetime.now(timezone.utc)
    await db.commit()

    # Dispatch execution in background
    from app.services.task_executor import task_executor
    asyncio.create_task(task_executor.execute(str(task.id)))

    return ResponseModel(message="任务已启动")


@router.post("/{task_id}/cancel", response_model=ResponseModel)
async def cancel_task(task_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Task).where(Task.id == task_id, Task.deleted_at.is_(None)))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail={"code": "TASK_NOT_FOUND", "message": "任务不存在"})
    if task.status in ("SUCCESS", "FAILED", "CANCELLED"):
        raise HTTPException(status_code=400, detail={"code": "INVALID_STATUS", "message": f"任务状态为 {task.status}，无法取消"})
    task.status = "CANCELLED"
    task.finished_at = datetime.now(timezone.utc)
    await db.commit()
    return ResponseModel(message="任务已取消")


@router.get("/{task_id}/logs", response_model=ResponseModel)
async def get_task_logs(
    task_id: str,
    level: str = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(TaskLog).where(TaskLog.task_id == task_id, TaskLog.deleted_at.is_(None))
    if level:
        query = query.where(TaskLog.level == level.upper())
    result = await db.execute(query.order_by(TaskLog.timestamp))
    logs = result.scalars().all()
    return ResponseModel(data=[{"level": l.level, "message": l.message, "timestamp": str(l.timestamp)} for l in logs])
