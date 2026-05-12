"""Task API tests — 25 E2E cases."""

import pytest
from httpx import AsyncClient
from tests.conftest import auth_header


async def _create_case(client, h, name="Task Case"):
    """Helper: create a case and return its ID."""
    resp = await client.post("/api/v1/cases", headers=h, json={"name": name, "type": "API"})
    assert resp.status_code == 201
    return resp.json()["data"]["id"]


# ── TC-TASK-001: Create immediate task ─────────────────────────
@pytest.mark.asyncio
async def test_create_task(client: AsyncClient, auth_token: str):
    h = auth_header(auth_token)
    case_id = await _create_case(client, h)
    resp = await client.post("/api/v1/tasks", headers=h, json={
        "name": "回归测试任务", "priority": "HIGH", "case_ids": [case_id],
    })
    assert resp.status_code == 201
    assert resp.json()["code"] == 0


# ── TC-TASK-002: Scheduled task (placeholder) ──────────────────
@pytest.mark.asyncio
async def test_create_scheduled_task(client: AsyncClient, auth_token: str):
    h = auth_header(auth_token)
    case_id = await _create_case(client, h)
    resp = await client.post("/api/v1/tasks", headers=h, json={
        "name": "定时任务", "case_ids": [case_id],
    })
    assert resp.status_code == 201


# ── TC-TASK-003: Empty name → 422 ─────────────────────────────
@pytest.mark.asyncio
async def test_create_task_empty_name(client: AsyncClient, auth_token: str):
    h = auth_header(auth_token)
    case_id = await _create_case(client, h)
    resp = await client.post("/api/v1/tasks", headers=h, json={
        "name": "", "case_ids": [case_id],
    })
    assert resp.status_code == 422


# ── TC-TASK-004~006: Validation cases ──────────────────────────
@pytest.mark.asyncio
async def test_create_task_default_priority(client: AsyncClient, auth_token: str):
    h = auth_header(auth_token)
    case_id = await _create_case(client, h)
    resp = await client.post("/api/v1/tasks", headers=h, json={
        "name": "默认优先级", "case_ids": [case_id],
    })
    assert resp.status_code == 201


# ── TC-TASK-007: Default priority is MEDIUM ────────────────────
@pytest.mark.asyncio
async def test_task_default_priority_medium(client: AsyncClient, auth_token: str):
    h = auth_header(auth_token)
    case_id = await _create_case(client, h)
    resp = await client.post("/api/v1/tasks", headers=h, json={"name": "Pri Task", "case_ids": [case_id]})
    task_id = resp.json()["data"]["id"]
    detail = await client.get(f"/api/v1/tasks/{task_id}", headers=h)
    assert detail.json()["data"]["priority"] == "MEDIUM"


# ── TC-TASK-008~011: Scheduling (placeholder) ──────────────────
@pytest.mark.asyncio
async def test_priority_scheduling_order(client: AsyncClient, auth_token: str):
    h = auth_header(auth_token)
    case_id = await _create_case(client, h)
    await client.post("/api/v1/tasks", headers=h, json={"name": "LOW", "priority": "LOW", "case_ids": [case_id]})
    await client.post("/api/v1/tasks", headers=h, json={"name": "HIGH", "priority": "HIGH", "case_ids": [case_id]})
    resp = await client.get("/api/v1/tasks", headers=h)
    assert resp.status_code == 200


# ── TC-TASK-012: Start task → RUNNING ──────────────────────────
@pytest.mark.asyncio
async def test_start_task(client: AsyncClient, auth_token: str):
    h = auth_header(auth_token)
    case_id = await _create_case(client, h)
    create_resp = await client.post("/api/v1/tasks", headers=h, json={"name": "Start Task", "case_ids": [case_id]})
    task_id = create_resp.json()["data"]["id"]

    resp = await client.post(f"/api/v1/tasks/{task_id}/start", headers=h)
    assert resp.status_code == 200

    detail = await client.get(f"/api/v1/tasks/{task_id}", headers=h)
    assert detail.json()["data"]["status"] == "RUNNING"


# ── TC-TASK-013: Cancel running task ───────────────────────────
@pytest.mark.asyncio
async def test_cancel_running_task(client: AsyncClient, auth_token: str):
    h = auth_header(auth_token)
    case_id = await _create_case(client, h, "Cancel Case")
    create_resp = await client.post("/api/v1/tasks", headers=h, json={"name": "Cancel Task", "case_ids": [case_id]})
    task_id = create_resp.json()["data"]["id"]

    await client.post(f"/api/v1/tasks/{task_id}/start", headers=h)
    resp = await client.post(f"/api/v1/tasks/{task_id}/cancel", headers=h)
    assert resp.status_code == 200

    detail = await client.get(f"/api/v1/tasks/{task_id}", headers=h)
    assert detail.json()["data"]["status"] == "CANCELLED"


# ── TC-TASK-014: Cancel pending task ───────────────────────────
@pytest.mark.asyncio
async def test_cancel_pending_task(client: AsyncClient, auth_token: str):
    h = auth_header(auth_token)
    case_id = await _create_case(client, h, "Pending Cancel Case")
    create_resp = await client.post("/api/v1/tasks", headers=h, json={"name": "Pending Cancel", "case_ids": [case_id]})
    task_id = create_resp.json()["data"]["id"]

    resp = await client.post(f"/api/v1/tasks/{task_id}/cancel", headers=h)
    assert resp.status_code == 200


# ── TC-TASK-017: Start non-PENDING task → 400 ─────────────────
@pytest.mark.asyncio
async def test_start_non_pending_task(client: AsyncClient, auth_token: str):
    h = auth_header(auth_token)
    case_id = await _create_case(client, h, "Double Start Case")
    create_resp = await client.post("/api/v1/tasks", headers=h, json={"name": "Double Start", "case_ids": [case_id]})
    task_id = create_resp.json()["data"]["id"]

    await client.post(f"/api/v1/tasks/{task_id}/start", headers=h)
    resp = await client.post(f"/api/v1/tasks/{task_id}/start", headers=h)
    assert resp.status_code in (400, 409)


# ── TC-TASK-018: Cancel completed task → 400 ──────────────────
@pytest.mark.asyncio
async def test_cancel_completed_task(client: AsyncClient, auth_token: str):
    h = auth_header(auth_token)
    case_id = await _create_case(client, h, "Completed Cancel Case")
    create_resp = await client.post("/api/v1/tasks", headers=h, json={"name": "Completed Cancel", "case_ids": [case_id]})
    task_id = create_resp.json()["data"]["id"]

    await client.post(f"/api/v1/tasks/{task_id}/start", headers=h)
    await client.post(f"/api/v1/tasks/{task_id}/cancel", headers=h)
    resp = await client.post(f"/api/v1/tasks/{task_id}/cancel", headers=h)
    assert resp.status_code in (400, 409)


# ── TC-TASK-019: Operate nonexistent task → 404 ───────────────
@pytest.mark.asyncio
async def test_operate_nonexistent_task(client: AsyncClient, auth_token: str):
    h = auth_header(auth_token)
    resp = await client.post("/api/v1/tasks/00000000-0000-0000-0000-000000000000/start", headers=h)
    assert resp.status_code == 404


# ── TC-TASK-020: View task logs ────────────────────────────────
@pytest.mark.asyncio
async def test_task_logs(client: AsyncClient, auth_token: str):
    h = auth_header(auth_token)
    case_id = await _create_case(client, h, "Log Case")
    create_resp = await client.post("/api/v1/tasks", headers=h, json={"name": "Log Task", "case_ids": [case_id]})
    task_id = create_resp.json()["data"]["id"]

    resp = await client.get(f"/api/v1/tasks/{task_id}/logs", headers=h)
    assert resp.status_code == 200


# ── TC-TASK-022: Logs for nonexistent task ─────────────────────
@pytest.mark.asyncio
async def test_logs_nonexistent_task(client: AsyncClient, auth_token: str):
    h = auth_header(auth_token)
    resp = await client.get("/api/v1/tasks/00000000-0000-0000-0000-000000000000/logs", headers=h)
    assert resp.status_code in (200, 404)


# ── TC-TASK-023~025: Task list filtering ───────────────────────
@pytest.mark.asyncio
async def test_list_tasks(client: AsyncClient, auth_token: str):
    resp = await client.get("/api/v1/tasks", headers=auth_header(auth_token))
    assert resp.status_code == 200
    assert "list" in resp.json()["data"]


@pytest.mark.asyncio
async def test_filter_tasks_by_status(client: AsyncClient, auth_token: str):
    h = auth_header(auth_token)
    resp = await client.get("/api/v1/tasks?status=PENDING", headers=h)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_filter_tasks_by_priority(client: AsyncClient, auth_token: str):
    h = auth_header(auth_token)
    resp = await client.get("/api/v1/tasks?priority=HIGH", headers=h)
    assert resp.status_code == 200


# ── TC-TASK: Start and cancel integration ──────────────────────
@pytest.mark.asyncio
async def test_start_and_cancel_task(client: AsyncClient, auth_token: str):
    h = auth_header(auth_token)
    case_id = await _create_case(client, h, "启停用例")
    create_resp = await client.post("/api/v1/tasks", headers=h, json={"name": "启停测试任务", "case_ids": [case_id]})
    task_id = create_resp.json()["data"]["id"]

    resp = await client.post(f"/api/v1/tasks/{task_id}/start", headers=h)
    assert resp.status_code == 200

    resp = await client.post(f"/api/v1/tasks/{task_id}/cancel", headers=h)
    assert resp.status_code == 200


# ── TC-TASK-DETAIL: Task detail returns cases list ──────────────
@pytest.mark.asyncio
async def test_task_detail_returns_cases(client: AsyncClient, auth_token: str):
    """Task detail should include the associated cases list."""
    h = auth_header(auth_token)

    # Create a case first
    case_resp = await client.post("/api/v1/cases", headers=h, json={
        "name": "关联用例", "type": "API", "priority": "P1",
        "steps": [], "assertions": [],
    })
    assert case_resp.status_code == 201
    case_id = case_resp.json()["data"]["id"]

    # Create task with the case
    task_resp = await client.post("/api/v1/tasks", headers=h, json={
        "name": "含用例任务", "case_ids": [case_id],
    })
    assert task_resp.status_code == 201
    task_id = task_resp.json()["data"]["id"]

    # Get task detail — should include cases
    detail = await client.get(f"/api/v1/tasks/{task_id}", headers=h)
    assert detail.status_code == 200
    data = detail.json()["data"]
    assert "cases" in data
    assert len(data["cases"]) == 1
    assert data["cases"][0]["case_id"] == case_id
    assert data["cases"][0]["case_name"] == "关联用例"


# ── TC-TASK-DETAIL: Task detail with cases ─────────────────────
@pytest.mark.asyncio
async def test_task_detail_empty_cases(client: AsyncClient, auth_token: str):
    """Task created with cases should return cases list."""
    h = auth_header(auth_token)
    case_id = await _create_case(client, h, "空详情用例")
    task_resp = await client.post("/api/v1/tasks", headers=h, json={"name": "用例任务", "case_ids": [case_id]})
    task_id = task_resp.json()["data"]["id"]

    detail = await client.get(f"/api/v1/tasks/{task_id}", headers=h)
    data = detail.json()["data"]
    assert "cases" in data
    assert len(data["cases"]) == 1


# ── TC-TASK-003: Empty case_ids → 422 ──────────────────────────
@pytest.mark.asyncio
async def test_create_task_empty_cases_422(client: AsyncClient, auth_token: str):
    h = auth_header(auth_token)
    resp = await client.post("/api/v1/tasks", headers=h, json={
        "name": "空用例任务", "case_ids": [],
    })
    assert resp.status_code == 422


# ── TC-TASK-004: case_ids > 100 → 422 ─────────────────────────
@pytest.mark.asyncio
async def test_create_task_max_cases_422(client: AsyncClient, auth_token: str):
    h = auth_header(auth_token)
    fake_ids = [str(i) for i in range(101)]
    resp = await client.post("/api/v1/tasks", headers=h, json={
        "name": "超限任务", "case_ids": fake_ids,
    })
    assert resp.status_code == 422


# ── TC-TASK-005: Nonexistent case → 404 ───────────────────────
@pytest.mark.asyncio
async def test_create_task_nonexistent_case_404(client: AsyncClient, auth_token: str):
    h = auth_header(auth_token)
    resp = await client.post("/api/v1/tasks", headers=h, json={
        "name": "不存在用例任务", "case_ids": ["00000000-0000-0000-0000-000000000000"],
    })
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "CASE_NOT_FOUND"


# ── TC-TASK-001: Create with execute_type ─────────────────────
@pytest.mark.asyncio
async def test_create_task_with_execute_type(client: AsyncClient, auth_token: str):
    h = auth_header(auth_token)
    # First create a valid case
    case_resp = await client.post("/api/v1/cases", headers=h, json={
        "name": "任务关联用例", "type": "API",
    })
    case_id = case_resp.json()["data"]["id"]

    resp = await client.post("/api/v1/tasks", headers=h, json={
        "name": "立即执行任务", "case_ids": [case_id], "execute_type": "IMMEDIATE",
    })
    assert resp.status_code == 201


# ── TC-TASK-002: Scheduled task with cron ─────────────────────
@pytest.mark.asyncio
async def test_create_scheduled_task_with_cron(client: AsyncClient, auth_token: str):
    h = auth_header(auth_token)
    case_resp = await client.post("/api/v1/cases", headers=h, json={
        "name": "定时用例", "type": "API",
    })
    case_id = case_resp.json()["data"]["id"]

    resp = await client.post("/api/v1/tasks", headers=h, json={
        "name": "定时任务", "case_ids": [case_id],
        "execute_type": "SCHEDULED", "schedule_cron": "0 2 * * *",
    })
    assert resp.status_code == 201
    task_id = resp.json()["data"]["id"]

    detail = await client.get(f"/api/v1/tasks/{task_id}", headers=h)
    data = detail.json()["data"]
    assert data["execute_type"] == "SCHEDULED"
    assert data["schedule_cron"] == "0 2 * * *"


# ── TC-TASK-007: Default execute_type is IMMEDIATE ────────────
@pytest.mark.asyncio
async def test_task_default_execute_type(client: AsyncClient, auth_token: str):
    h = auth_header(auth_token)
    case_id = await _create_case(client, h, "默认类型用例")
    resp = await client.post("/api/v1/tasks", headers=h, json={
        "name": "默认执行类型", "case_ids": [case_id],
    })
    assert resp.status_code == 201
    task_id = resp.json()["data"]["id"]
    detail = await client.get(f"/api/v1/tasks/{task_id}", headers=h)
    assert detail.json()["data"]["execute_type"] == "IMMEDIATE"


# ── TC-TASK-021: Log level filter works correctly ─────────────
@pytest.mark.asyncio
async def test_task_logs_filter_by_level(client: AsyncClient, auth_token: str, test_engine):
    """GET /tasks/{id}/logs?level=ERROR should only return ERROR logs."""
    from app.models.task import TaskLog
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    h = auth_header(auth_token)
    case_id = await _create_case(client, h, "日志用例")
    task_resp = await client.post("/api/v1/tasks", headers=h, json={"name": "日志筛选任务", "case_ids": [case_id]})
    task_id = task_resp.json()["data"]["id"]

    # Insert logs of different levels directly via DB
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        import uuid as _uuid
        task_uuid = _uuid.UUID(task_id)
        for level, msg in [("INFO", "info msg"), ("ERROR", "error msg"), ("WARNING", "warn msg"), ("ERROR", "error msg 2")]:
            session.add(TaskLog(task_id=task_uuid, level=level, message=msg))
        await session.commit()

    # Filter by ERROR
    resp = await client.get(f"/api/v1/tasks/{task_id}/logs?level=ERROR", headers=h)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 2
    for log in data:
        assert log["level"] == "ERROR"

    # Filter by INFO
    resp = await client.get(f"/api/v1/tasks/{task_id}/logs?level=INFO", headers=h)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 1
    assert data[0]["level"] == "INFO"


# ── TC-TASK-023: Task list has all required fields ────────────
@pytest.mark.asyncio
async def test_task_list_has_all_fields(client: AsyncClient, auth_token: str):
    h = auth_header(auth_token)
    resp = await client.get("/api/v1/tasks", headers=h)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "list" in data
    assert "pagination" in data
    if data["list"]:
        item = data["list"][0]
        for field in ("id", "name", "status", "priority", "total_cases", "created_at"):
            assert field in item, f"Missing field: {field}"


# ── TC-TASK-DETAIL: Task detail with case names ───────────────
@pytest.mark.asyncio
async def test_task_detail_with_case_info(client: AsyncClient, auth_token: str):
    h = auth_header(auth_token)
    case_resp = await client.post("/api/v1/cases", headers=h, json={
        "name": "详情用例", "type": "UI", "priority": "P0",
    })
    case_id = case_resp.json()["data"]["id"]

    task_resp = await client.post("/api/v1/tasks", headers=h, json={
        "name": "详情任务", "case_ids": [case_id],
    })
    task_id = task_resp.json()["data"]["id"]

    detail = await client.get(f"/api/v1/tasks/{task_id}", headers=h)
    data = detail.json()["data"]
    assert data["name"] == "详情任务"
    assert data["status"] == "PENDING"
    assert data["total_cases"] == 1
    assert "cases" in data
    assert len(data["cases"]) == 1
    assert data["cases"][0]["case_name"] == "详情用例"
    assert data["cases"][0]["case_type"] == "UI"
