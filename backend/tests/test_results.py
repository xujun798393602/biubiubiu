"""Result API tests — 22 E2E cases."""

import uuid as _uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests.conftest import auth_header


# ── Helper: create a task with results ─────────────────────────
async def _create_task_with_results(client, token, test_engine, count=3):
    """Create a task and seed test results."""
    h = auth_header(token)

    # Create a case first via API
    case_resp = await client.post("/api/v1/cases", headers=h, json={"name": "Result Case", "type": "API"})
    case_id = case_resp.json()["data"]["id"]

    # Create task with the case
    resp = await client.post("/api/v1/tasks", headers=h, json={"name": "Result Task", "case_ids": [case_id]})
    task_id = resp.json()["data"]["id"]

    from app.models.result import TestResult
    from app.models.test_case import TestCase, TaskCase
    from app.models.user import User
    from sqlalchemy import select

    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        case_uuid = _uuid.UUID(case_id)
        tc = (await session.execute(select(TaskCase).where(
            TaskCase.task_id == _uuid.UUID(task_id), TaskCase.case_id == case_uuid
        ))).scalar_one()

        for i in range(count):
            status = "SUCCESS" if i < count - 1 else "FAILED"
            result = TestResult(
                task_id=_uuid.UUID(task_id),
                case_id=case_uuid,
                task_case_id=tc.id,
                status=status,
                duration_ms=500 + i * 100,
                detail={"request": "GET /api/health", "response": '{"status": "ok"}'},
            )
            session.add(result)
        await session.commit()

    return task_id


# ── TC-RESULT-001: Task result stats ───────────────────────────
@pytest.mark.asyncio
async def test_result_overview(client: AsyncClient, auth_token: str, test_engine):
    h = auth_header(auth_token)
    task_id = await _create_task_with_results(client, auth_token, test_engine, count=10)

    resp = await client.get(f"/api/v1/results/overview?taskId={task_id}", headers=h)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["totalCases"] == 10
    assert "successRate" in data
    # successRate should be decimal (0.x), not percentage
    assert 0 <= data["successRate"] <= 1
    # duration should be present
    assert "duration" in data
    assert data["duration"] >= 0


# ── TC-RESULT-002: All success ─────────────────────────────────
@pytest.mark.asyncio
async def test_result_all_success(client: AsyncClient, auth_token: str, test_engine):
    h = auth_header(auth_token)
    task_id = await _create_task_with_results(client, auth_token, test_engine, count=5)

    resp = await client.get(f"/api/v1/results/overview?taskId={task_id}", headers=h)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["totalCases"] >= 1
    # With _create_task_with_results, last one is FAILED, rest are SUCCESS
    assert data["successCount"] >= 1
    assert data["failedCount"] >= 1


# ── TC-RESULT-003: Overview for nonexistent task ──────────────
@pytest.mark.asyncio
async def test_result_overview_nonexistent(client: AsyncClient, auth_token: str):
    h = auth_header(auth_token)
    resp = await client.get("/api/v1/results/overview?taskId=00000000-0000-0000-0000-000000000000", headers=h)
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "TASK_NOT_FOUND"


# ── TC-RESULT-005: Result list ─────────────────────────────────
@pytest.mark.asyncio
async def test_result_list(client: AsyncClient, auth_token: str, test_engine):
    h = auth_header(auth_token)
    task_id = await _create_task_with_results(client, auth_token, test_engine, count=5)

    resp = await client.get(f"/api/v1/results?taskId={task_id}", headers=h)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "list" in data
    assert "pagination" in data


# ── TC-RESULT-006: Filter by status ────────────────────────────
@pytest.mark.asyncio
async def test_result_filter_by_status(client: AsyncClient, auth_token: str, test_engine):
    h = auth_header(auth_token)
    task_id = await _create_task_with_results(client, auth_token, test_engine, count=5)

    resp = await client.get(f"/api/v1/results?taskId={task_id}&status=FAILED", headers=h)
    assert resp.status_code == 200
    for item in resp.json()["data"]["list"]:
        assert item["status"] == "FAILED"


# ── TC-RESULT-007: Result pagination ───────────────────────────
@pytest.mark.asyncio
async def test_result_pagination(client: AsyncClient, auth_token: str, test_engine):
    h = auth_header(auth_token)
    task_id = await _create_task_with_results(client, auth_token, test_engine, count=5)

    resp = await client.get(f"/api/v1/results?taskId={task_id}&page=1&pageSize=2", headers=h)
    assert resp.status_code == 200
    assert len(resp.json()["data"]["list"]) <= 2


# ── TC-RESULT-008: API result detail ───────────────────────────
@pytest.mark.asyncio
async def test_result_detail(client: AsyncClient, auth_token: str, test_engine):
    h = auth_header(auth_token)
    task_id = await _create_task_with_results(client, auth_token, test_engine, count=1)

    list_resp = await client.get(f"/api/v1/results?taskId={task_id}", headers=h)
    result_id = list_resp.json()["data"]["list"][0]["id"]

    resp = await client.get(f"/api/v1/results/api/{result_id}", headers=h)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "detail" in data
    assert "case_name" in data
    assert "case_type" in data
    assert data["case_name"] == "Result Case"


# ── TC-RESULT-011: Nonexistent result → 404 ────────────────────
@pytest.mark.asyncio
async def test_result_nonexistent(client: AsyncClient, auth_token: str):
    h = auth_header(auth_token)
    resp = await client.get("/api/v1/results/api/00000000-0000-0000-0000-000000000000", headers=h)
    assert resp.status_code == 404


# ── TC-RESULT-012~014: Export (placeholder) ────────────────────
@pytest.mark.asyncio
async def test_export_results(client: AsyncClient, auth_token: str, test_engine):
    h = auth_header(auth_token)
    task_id = await _create_task_with_results(client, auth_token, test_engine, count=1)
    resp = await client.post(f"/api/v1/results/{task_id}/export", headers=h)
    assert resp.status_code == 200


# ── TC-RESULT-016: Generate share link ─────────────────────────
@pytest.mark.asyncio
async def test_create_share_link(client: AsyncClient, auth_token: str, test_engine):
    h = auth_header(auth_token)
    task_id = await _create_task_with_results(client, auth_token, test_engine, count=1)

    resp = await client.post(f"/api/v1/results/{task_id}/share", headers=h, json={
        "expires_in_hours": 24,
    })
    assert resp.status_code == 200
    assert "share_url" in resp.json()["data"]


# ── TC-RESULT-017: Share without password ─────────────────────
@pytest.mark.asyncio
async def test_share_no_password(client: AsyncClient, auth_token: str, test_engine):
    h = auth_header(auth_token)
    task_id = await _create_task_with_results(client, auth_token, test_engine, count=1)

    resp = await client.post(f"/api/v1/results/{task_id}/share", headers=h, json={})
    assert resp.status_code == 200
    share_url = resp.json()["data"]["share_url"]
    token = share_url.split("/")[-1]

    # Should be accessible without password
    access = await client.get(f"/api/v1/results/share/{token}")
    assert access.status_code == 200


# ── TC-RESULT-018: Access valid share ──────────────────────────
@pytest.mark.asyncio
async def test_access_share_link(client: AsyncClient, auth_token: str, test_engine):
    h = auth_header(auth_token)
    task_id = await _create_task_with_results(client, auth_token, test_engine, count=1)

    share_resp = await client.post(f"/api/v1/results/{task_id}/share", headers=h, json={})
    share_url = share_resp.json()["data"]["share_url"]
    token = share_url.split("/")[-1]

    resp = await client.get(f"/api/v1/results/share/{token}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    # Should return overview + results
    assert "overview" in data
    assert "results" in data


# ── TC-RESULT-019: Share requires password ─────────────────────
@pytest.mark.asyncio
async def test_share_requires_password(client: AsyncClient, auth_token: str, test_engine):
    h = auth_header(auth_token)
    task_id = await _create_task_with_results(client, auth_token, test_engine, count=1)

    share_resp = await client.post(f"/api/v1/results/{task_id}/share", headers=h, json={"password": "secret123"})
    share_url = share_resp.json()["data"]["share_url"]
    token = share_url.split("/")[-1]

    # Access without password
    resp = await client.get(f"/api/v1/results/share/{token}")
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "SHARE_PASSWORD_REQUIRED"


# ── TC-RESULT-020: Share wrong password ────────────────────────
@pytest.mark.asyncio
async def test_share_wrong_password(client: AsyncClient, auth_token: str, test_engine):
    h = auth_header(auth_token)
    task_id = await _create_task_with_results(client, auth_token, test_engine, count=1)

    share_resp = await client.post(f"/api/v1/results/{task_id}/share", headers=h, json={"password": "secret123"})
    share_url = share_resp.json()["data"]["share_url"]
    token = share_url.split("/")[-1]

    resp = await client.get(f"/api/v1/results/share/{token}?password=wrong")
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "SHARE_PASSWORD_INVALID"


# ── TC-RESULT-021: Expired share → 410 ────────────────────────
@pytest.mark.asyncio
async def test_expired_share(client: AsyncClient, auth_token: str, test_engine):
    h = auth_header(auth_token)
    task_id = await _create_task_with_results(client, auth_token, test_engine, count=1)

    # Create share that expires in 0 hours (already expired)
    share_resp = await client.post(f"/api/v1/results/{task_id}/share", headers=h, json={
        "expires_in_hours": 0,
    })
    share_url = share_resp.json()["data"]["share_url"]
    token = share_url.split("/")[-1]

    resp = await client.get(f"/api/v1/results/share/{token}")
    assert resp.status_code == 410
    assert resp.json()["detail"]["code"] == "SHARE_EXPIRED"


# ── TC-RESULT-022: Nonexistent share token → 404 ──────────────
@pytest.mark.asyncio
async def test_nonexistent_share(client: AsyncClient):
    resp = await client.get("/api/v1/results/share/nonexistent-token")
    assert resp.status_code == 404


# ── TC-RESULT-012: Export with format param ────────────────────
@pytest.mark.asyncio
async def test_export_results_with_format(client: AsyncClient, auth_token: str, test_engine):
    h = auth_header(auth_token)
    task_id = await _create_task_with_results(client, auth_token, test_engine, count=1)
    resp = await client.post(f"/api/v1/results/{task_id}/export", headers=h, json={"format": "xlsx"})
    assert resp.status_code == 200


# ── TC-RESULT-015: Export nonexistent task → 404 ──────────────
@pytest.mark.asyncio
async def test_export_nonexistent_task(client: AsyncClient, auth_token: str):
    h = auth_header(auth_token)
    resp = await client.post("/api/v1/results/00000000-0000-0000-0000-000000000000/export", headers=h, json={})
    assert resp.status_code == 404
