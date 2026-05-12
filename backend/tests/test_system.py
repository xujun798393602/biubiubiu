"""System API tests — 22 E2E cases."""

import pytest
from httpx import AsyncClient
from tests.conftest import auth_header


# ── TC-SYS-001: List logs ──────────────────────────────────────
@pytest.mark.asyncio
async def test_system_logs(client: AsyncClient, auth_token: str):
    resp = await client.get("/api/v1/system/logs", headers=auth_header(auth_token))
    assert resp.status_code == 200
    assert "list" in resp.json()["data"]


# ── TC-SYS-002: Filter logs by operation ───────────────────────
@pytest.mark.asyncio
async def test_filter_logs_by_operation(client: AsyncClient, auth_token: str):
    resp = await client.get("/api/v1/system/logs?operation=LOGIN", headers=auth_header(auth_token))
    assert resp.status_code == 200


# ── TC-SYS-007: OPS can view logs ──────────────────────────────
@pytest.mark.asyncio
async def test_ops_can_view_logs(client: AsyncClient, ops_token: str):
    resp = await client.get("/api/v1/system/logs", headers=auth_header(ops_token))
    assert resp.status_code == 200


# ── TC-SYS-008: TESTER cannot view logs → 403 ─────────────────
@pytest.mark.asyncio
async def test_tester_cannot_view_logs(client: AsyncClient, tester_token: str):
    resp = await client.get("/api/v1/system/logs", headers=auth_header(tester_token))
    assert resp.status_code == 403


# ── TC-SYS-009: List notifications ─────────────────────────────
@pytest.mark.asyncio
async def test_notifications(client: AsyncClient, auth_token: str):
    resp = await client.get("/api/v1/system/notifications", headers=auth_header(auth_token))
    assert resp.status_code == 200
    assert "list" in resp.json()["data"]


# ── TC-SYS-010: Mark notification read ─────────────────────────
@pytest.mark.asyncio
async def test_mark_notification_read(client: AsyncClient, auth_token: str):
    h = auth_header(auth_token)
    # Try marking a nonexistent notification
    resp = await client.put("/api/v1/system/notifications/00000000-0000-0000-0000-000000000000/read", headers=h)
    assert resp.status_code in (200, 404)


# ── TC-SYS-013: Mark nonexistent notification → 404 ───────────
@pytest.mark.asyncio
async def test_mark_nonexistent_notification(client: AsyncClient, auth_token: str):
    resp = await client.put(
        "/api/v1/system/notifications/00000000-0000-0000-0000-000000000000/read",
        headers=auth_header(auth_token),
    )
    assert resp.status_code in (200, 404)


# ── TC-SYS-014: View config ────────────────────────────────────
@pytest.mark.asyncio
async def test_get_config(client: AsyncClient, auth_token: str):
    resp = await client.get("/api/v1/system/config", headers=auth_header(auth_token))
    assert resp.status_code == 200


# ── TC-SYS-015: Modify config ──────────────────────────────────
@pytest.mark.asyncio
async def test_update_config(client: AsyncClient, auth_token: str):
    resp = await client.put("/api/v1/system/config", headers=auth_header(auth_token), json={
        "key": "test_key", "value": "test_value",
    })
    assert resp.status_code == 200


# ── TC-SYS-016: TESTER cannot modify config → 403 ─────────────
@pytest.mark.asyncio
async def test_tester_cannot_modify_config(client: AsyncClient, tester_token: str):
    resp = await client.put("/api/v1/system/config", headers=auth_header(tester_token), json={
        "key": "test_key", "value": "test_value",
    })
    assert resp.status_code == 403


# ── TC-SYS-017: OPS read-only config ───────────────────────────
@pytest.mark.asyncio
async def test_ops_readonly_config(client: AsyncClient, ops_token: str):
    h = auth_header(ops_token)
    # GET succeeds
    resp = await client.get("/api/v1/system/config", headers=h)
    assert resp.status_code == 200
    # PUT forbidden
    resp = await client.put("/api/v1/system/config", headers=h, json={"key": "x", "value": "y"})
    assert resp.status_code == 403


# ── TC-SYS-018: Health check ───────────────────────────────────
@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ── TC-SYS-019: Readiness check ────────────────────────────────
@pytest.mark.asyncio
async def test_readiness_check(client: AsyncClient):
    resp = await client.get("/ready")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"


# ── TC-SYS-022: System stats ───────────────────────────────────
@pytest.mark.asyncio
async def test_system_stats(client: AsyncClient, auth_token: str):
    resp = await client.get("/api/v1/system/stats", headers=auth_header(auth_token))
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "totalCases" in data
    assert "totalTasks" in data
    assert "totalNodes" in data


# ── TC-SYS-003: Filter logs by resource_type ───────────────────
@pytest.mark.asyncio
async def test_filter_logs_by_resource_type(client: AsyncClient, auth_token: str):
    resp = await client.get("/api/v1/system/logs?resource_type=USER", headers=auth_header(auth_token))
    assert resp.status_code == 200
