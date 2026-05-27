"""Test results endpoints."""

import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, hash_password, verify_password
from app.models.result import TestResult, ResultShare
from app.models.task import Task
from app.models.test_case import TestCase
from app.models.user import User
from app.schemas.common import ResponseModel
from app.schemas.result import ResultItem, ResultOverview, ShareCreate

router = APIRouter()


@router.get("/overview", response_model=ResponseModel)
async def get_result_overview(
    taskId: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify task exists
    task = (await db.execute(select(Task).where(Task.id == taskId, Task.deleted_at.is_(None)))).scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail={"code": "TASK_NOT_FOUND", "message": "任务不存在"})

    results = (await db.execute(select(TestResult).where(TestResult.task_id == taskId, TestResult.deleted_at.is_(None)))).scalars().all()
    total = len(results)
    success = sum(1 for r in results if r.status == "SUCCESS")
    failed = sum(1 for r in results if r.status == "FAILED")
    skipped = sum(1 for r in results if r.status == "SKIPPED")
    total_duration = sum(r.duration_ms for r in results)
    executed = success + failed  # 实际执行的用例数（排除跳过）
    success_rate = round(success / executed * 100, 1) if executed else 0

    return ResponseModel(data={
        "totalCases": total,
        "successCount": success,
        "failedCount": failed,
        "skippedCount": skipped,
        "successRate": success_rate,
        "duration": total_duration,
    })


@router.get("", response_model=ResponseModel)
async def list_results(
    taskId: str = Query(...),
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    status: str = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(TestResult).where(TestResult.task_id == taskId, TestResult.deleted_at.is_(None))
    count_query = select(func.count()).select_from(TestResult).where(TestResult.task_id == taskId, TestResult.deleted_at.is_(None))

    if status:
        query = query.where(TestResult.status == status)
        count_query = count_query.where(TestResult.status == status)

    total = (await db.execute(count_query)).scalar()
    items = (await db.execute(query.offset((page - 1) * pageSize).limit(pageSize))).scalars().all()

    # Enrich with case info
    result_list = []
    for item in items:
        case = (await db.execute(select(TestCase).where(TestCase.id == item.case_id))).scalar_one_or_none()
        result_list.append(ResultItem(
            id=str(item.id),
            task_id=str(item.task_id),
            case_id=str(item.case_id),
            caseName=case.name if case else "",
            caseType=case.type if case else "",
            status=item.status,
            duration=item.duration_ms / 1000,
            startedAt=str(item.started_at) if item.started_at else None,
            finishedAt=str(item.finished_at) if item.finished_at else None,
        ))

    return ResponseModel(data={
        "list": result_list,
        "pagination": {"page": page, "pageSize": pageSize, "total": total, "totalPages": (total + pageSize - 1) // pageSize},
    })


@router.get("/by-case/{case_id}", response_model=ResponseModel)
async def get_results_by_case(case_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Return all test results for a specific case (used by Locust historical results page)."""
    try:
        uuid.UUID(case_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"code": "INVALID_ID", "message": "无效的用例ID"})

    case = (await db.execute(select(TestCase).where(TestCase.id == case_id, TestCase.deleted_at.is_(None)))).scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "用例不存在"})

    results = (await db.execute(
        select(TestResult).where(TestResult.case_id == case_id, TestResult.deleted_at.is_(None))
        .order_by(TestResult.created_at.desc())
    )).scalars().all()

    result_list = []
    for r in results:
        result_list.append({
            "id": str(r.id),
            "task_id": str(r.task_id),
            "status": r.status,
            "duration_ms": r.duration_ms,
            "detail": r.detail,
            "started_at": str(r.started_at) if r.started_at else None,
            "finished_at": str(r.finished_at) if r.finished_at else None,
        })

    return ResponseModel(data={
        "case_id": case_id,
        "case_name": case.name,
        "case_type": case.type,
        "results": result_list,
    })


@router.get("/perf-script/{case_id}")
async def get_perf_script(case_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Return the Locust script for a performance case as a downloadable file."""
    case = (await db.execute(select(TestCase).where(TestCase.id == case_id, TestCase.deleted_at.is_(None)))).scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "用例不存在"})
    if case.type != "PERFORMANCE" or not case.perf_script:
        raise HTTPException(status_code=400, detail={"code": "NOT_PERF_CASE", "message": "该用例不是性能压测类型或未配置脚本"})

    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(
        content=case.perf_script,
        media_type="text/x-python",
        headers={"Content-Disposition": f'attachment; filename="locust_{case_id[:8]}.py"'},
    )


@router.post("/sync-perf-script/{case_id}", response_model=ResponseModel)
async def sync_perf_script(case_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Sync a performance case's Locust script to the shared volume for the Locust Web UI."""
    # Validate UUID format (prevents path traversal)
    try:
        uuid.UUID(case_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"code": "INVALID_ID", "message": "无效的用例ID"})

    case = (await db.execute(select(TestCase).where(TestCase.id == case_id, TestCase.deleted_at.is_(None)))).scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "用例不存在"})
    if case.type != "PERFORMANCE" or not case.perf_script:
        raise HTTPException(status_code=400, detail={"code": "NOT_PERF_CASE", "message": "该用例不是性能压测类型或未配置脚本"})

    scripts_dir = Path("/scripts")
    scripts_dir.mkdir(parents=True, exist_ok=True)
    script_path = scripts_dir / f"{case_id}.py"
    meta_path = scripts_dir / f"{case_id}.json"

    try:
        script_path.write_text(case.perf_script, encoding="utf-8")
        # Write parameter metadata for the Locust webapp
        import json
        meta = {
            "case_id": case_id,
            "perf_url": case.perf_url or "",
            "perf_vusers": case.perf_vusers or 10,
            "perf_spawn_rate": case.perf_spawn_rate or 1,
            "perf_duration": case.perf_duration or 60,
            "case_name": case.name or "",
        }
        meta_path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail={"code": "WRITE_FAILED", "message": f"写入脚本文件失败: {e}"})

    return ResponseModel(data={"status": "ok", "case_id": case_id})


@router.get("/api/{result_id}", response_model=ResponseModel)
async def get_result_detail(result_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = (await db.execute(select(TestResult).where(TestResult.id == result_id, TestResult.deleted_at.is_(None)))).scalar_one_or_none()
    if not result:
        raise HTTPException(status_code=404, detail={"code": "RESULT_NOT_FOUND", "message": "结果不存在"})

    case = (await db.execute(select(TestCase).where(TestCase.id == result.case_id))).scalar_one_or_none()

    return ResponseModel(data={
        "id": str(result.id),
        "task_id": str(result.task_id),
        "case_id": str(result.case_id),
        "case_name": case.name if case else "",
        "case_type": case.type if case else "",
        "status": result.status,
        "detail": result.detail,
        "duration_ms": result.duration_ms,
    })


@router.post("/{task_id}/export", response_model=ResponseModel)
async def export_results(task_id: str, body: dict = None, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = (await db.execute(select(Task).where(Task.id == task_id, Task.deleted_at.is_(None)))).scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail={"code": "TASK_NOT_FOUND", "message": "任务不存在"})
    fmt = (body or {}).get("format", "xlsx")
    return ResponseModel(data={"format": fmt, "message": "导出功能待实现"})


@router.post("/{task_id}/share", response_model=ResponseModel)
async def create_share_link(
    task_id: str,
    body: ShareCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    token = uuid.uuid4().hex
    expires_at = None
    if body.expires_in_hours is not None:
        if body.expires_in_hours <= 0:
            expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        else:
            expires_at = datetime.now(timezone.utc) + timedelta(hours=body.expires_in_hours)

    # Get first result for this task
    result = (await db.execute(select(TestResult).where(TestResult.task_id == task_id, TestResult.deleted_at.is_(None)))).scalar_one_or_none()
    if not result:
        raise HTTPException(status_code=404, detail={"code": "NO_RESULTS", "message": "该任务无测试结果"})

    share = ResultShare(
        result_id=result.id,
        task_id=uuid.UUID(task_id),
        creator_id=current_user.id,
        token=token,
        password_hash=hash_password(body.password) if body.password else None,
        expires_at=expires_at,
    )
    db.add(share)
    await db.commit()
    return ResponseModel(data={"share_url": f"/share/{token}"})


@router.get("/share/{token}", response_model=ResponseModel)
async def get_share(token: str, password: str = Query(None), db: AsyncSession = Depends(get_db)):
    share = (await db.execute(select(ResultShare).where(ResultShare.token == token, ResultShare.deleted_at.is_(None)))).scalar_one_or_none()
    if not share:
        raise HTTPException(status_code=404, detail={"code": "SHARE_NOT_FOUND", "message": "分享链接不存在"})
    if share.expires_at and share.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail={"code": "SHARE_EXPIRED", "message": "分享链接已过期"})
    if share.password_hash:
        if not password:
            raise HTTPException(status_code=401, detail={"code": "SHARE_PASSWORD_REQUIRED", "message": "请输入访问密码"})
        if not verify_password(password, share.password_hash):
            raise HTTPException(status_code=401, detail={"code": "SHARE_PASSWORD_INVALID", "message": "密码错误"})

    share.access_count += 1
    await db.commit()

    # Return overview + results for the shared task
    results = (await db.execute(select(TestResult).where(TestResult.task_id == share.task_id, TestResult.deleted_at.is_(None)))).scalars().all()
    total = len(results)
    success = sum(1 for r in results if r.status == "SUCCESS")
    failed = sum(1 for r in results if r.status == "FAILED")
    overview = {
        "totalCases": total,
        "successCount": success,
        "failedCount": failed,
        "successRate": round(success / total, 2) if total else 0,
    }
    result_list = [{"id": str(r.id), "status": r.status, "duration_ms": r.duration_ms} for r in results]

    return ResponseModel(data={"overview": overview, "results": result_list})
