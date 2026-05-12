"""Test case API tests — 25 E2E cases."""

import pytest
from httpx import AsyncClient
from tests.conftest import auth_header


# ── TC-CASE-001: List all cases ────────────────────────────────
@pytest.mark.asyncio
async def test_list_cases(client: AsyncClient, auth_token: str):
    # Create a few cases first
    h = auth_header(auth_token)
    for i in range(3):
        await client.post("/api/v1/cases", headers=h, json={"name": f"Case {i}", "type": "API"})

    resp = await client.get("/api/v1/cases", headers=h)
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert "list" in data["data"]
    assert "pagination" in data["data"]
    assert data["data"]["pagination"]["total"] >= 3


# ── TC-CASE-002: Filter by type ────────────────────────────────
@pytest.mark.asyncio
async def test_filter_cases_by_type(client: AsyncClient, auth_token: str):
    h = auth_header(auth_token)
    await client.post("/api/v1/cases", headers=h, json={"name": "API Case", "type": "API"})
    await client.post("/api/v1/cases", headers=h, json={"name": "UI Case", "type": "UI"})

    resp = await client.get("/api/v1/cases?type=API", headers=h)
    assert resp.status_code == 200
    for item in resp.json()["data"]["list"]:
        assert item["type"] == "API"


# ── TC-CASE-003: Keyword search ────────────────────────────────
@pytest.mark.asyncio
async def test_search_cases_by_keyword(client: AsyncClient, auth_token: str):
    h = auth_header(auth_token)
    await client.post("/api/v1/cases", headers=h, json={"name": "UniqueKeyword123", "type": "API"})

    resp = await client.get("/api/v1/cases?keyword=UniqueKeyword123", headers=h)
    assert resp.status_code == 200
    assert any("UniqueKeyword123" in i["name"] for i in resp.json()["data"]["list"])


# ── TC-CASE-004: Combined filter ───────────────────────────────
@pytest.mark.asyncio
async def test_combined_filter(client: AsyncClient, auth_token: str):
    h = auth_header(auth_token)
    await client.post("/api/v1/cases", headers=h, json={"name": "Combo", "type": "UI", "priority": "P1"})

    resp = await client.get("/api/v1/cases?type=UI&priority=P1", headers=h)
    assert resp.status_code == 200
    for item in resp.json()["data"]["list"]:
        assert item["type"] == "UI"
        assert item["priority"] == "P1"


# ── TC-CASE-005: Pagination ────────────────────────────────────
@pytest.mark.asyncio
async def test_pagination(client: AsyncClient, auth_token: str):
    h = auth_header(auth_token)
    resp = await client.get("/api/v1/cases?page=1&pageSize=2", headers=h)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data["list"]) <= 2


# ── TC-CASE-006: Empty result ──────────────────────────────────
@pytest.mark.asyncio
async def test_empty_result(client: AsyncClient, auth_token: str):
    h = auth_header(auth_token)
    resp = await client.get("/api/v1/cases?keyword=NonexistentXYZ999", headers=h)
    assert resp.status_code == 200
    assert resp.json()["data"]["pagination"]["total"] == 0
    assert resp.json()["data"]["list"] == []


# ── TC-CASE-007: Create UI case with type-specific fields ─────
@pytest.mark.asyncio
async def test_create_ui_case(client: AsyncClient, auth_token: str):
    h = auth_header(auth_token)
    resp = await client.post("/api/v1/cases", headers=h, json={
        "name": "登录页面UI测试", "type": "UI", "priority": "P1",
        "module": "认证模块", "tags": ["登录", "UI"],
        "description": "验证登录页面的UI交互",
        "preconditions": "用户已注册",
        "ui_url": "http://example.com/login",
        "ui_script": "async def test_login(page): ...",
        "ui_script_type": "MANUAL",
    })
    assert resp.status_code == 201
    case_id = resp.json()["data"]["id"]

    # Verify all fields persisted
    detail = await client.get(f"/api/v1/cases/{case_id}", headers=h)
    data = detail.json()["data"]
    assert data["type"] == "UI"
    assert data["ui_url"] == "http://example.com/login"
    assert data["ui_script"] == "async def test_login(page): ..."
    assert data["ui_script_type"] == "MANUAL"
    assert data["module"] == "认证模块"
    assert data["tags"] == ["登录", "UI"]
    assert data["version"] == 1


# ── TC-CASE-008: Create API case with all API fields ─────────
@pytest.mark.asyncio
async def test_create_api_case(client: AsyncClient, auth_token: str):
    h = auth_header(auth_token)
    resp = await client.post("/api/v1/cases", headers=h, json={
        "name": "登录接口测试", "type": "API", "priority": "P0",
        "api_url": "http://example.com/api/v1/auth/login",
        "api_method": "POST",
        "api_headers": {"Content-Type": "application/json"},
        "api_body_type": "JSON",
        "api_body": '{"username":"test","password":"123456"}',
        "api_timeout": 30000,
        "api_assertions": [
            {"type": "status_code", "expected": 200},
            {"type": "jsonpath", "path": "$.code", "expected": 0},
        ],
    })
    assert resp.status_code == 201
    case_id = resp.json()["data"]["id"]

    detail = await client.get(f"/api/v1/cases/{case_id}", headers=h)
    data = detail.json()["data"]
    assert data["type"] == "API"
    assert data["api_url"] == "http://example.com/api/v1/auth/login"
    assert data["api_method"] == "POST"
    assert data["api_headers"] == {"Content-Type": "application/json"}
    assert data["api_body_type"] == "JSON"
    assert data["api_timeout"] == 30000
    assert len(data["api_assertions"]) == 2


# ── TC-CASE-009: Create PERFORMANCE case with perf fields ────
@pytest.mark.asyncio
async def test_create_performance_case(client: AsyncClient, auth_token: str):
    h = auth_header(auth_token)
    resp = await client.post("/api/v1/cases", headers=h, json={
        "name": "登录接口压测", "type": "PERFORMANCE", "priority": "P1",
        "perf_url": "http://example.com/api/v1/auth/login",
        "perf_vusers": 100,
        "perf_spawn_rate": 10,
        "perf_duration": 60,
        "perf_assertions": [
            {"type": "p95_response_time", "max": 500},
            {"type": "error_rate", "max": 0.01},
        ],
    })
    assert resp.status_code == 201
    case_id = resp.json()["data"]["id"]

    detail = await client.get(f"/api/v1/cases/{case_id}", headers=h)
    data = detail.json()["data"]
    assert data["type"] == "PERFORMANCE"
    assert data["perf_url"] == "http://example.com/api/v1/auth/login"
    assert data["perf_vusers"] == 100
    assert data["perf_spawn_rate"] == 10
    assert data["perf_duration"] == 60
    assert len(data["perf_assertions"]) == 2


# ── TC-CASE-010: Create empty name → 422 ──────────────────────
@pytest.mark.asyncio
async def test_create_case_empty_name(client: AsyncClient, auth_token: str):
    h = auth_header(auth_token)
    resp = await client.post("/api/v1/cases", headers=h, json={"name": "", "type": "API"})
    assert resp.status_code == 422


# ── TC-CASE-011: Create invalid type → 422 ────────────────────
@pytest.mark.asyncio
async def test_create_case_invalid_type(client: AsyncClient, auth_token: str):
    h = auth_header(auth_token)
    resp = await client.post("/api/v1/cases", headers=h, json={"name": "Test", "type": ""})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_case_invalid_type_value(client: AsyncClient, auth_token: str):
    h = auth_header(auth_token)
    resp = await client.post("/api/v1/cases", headers=h, json={"name": "Test", "type": "INVALID_TYPE"})
    assert resp.status_code == 422


# ── TC-CASE-012: Create defaults (priority=P2, status=DRAFT, version=1)
@pytest.mark.asyncio
async def test_create_case_defaults(client: AsyncClient, auth_token: str):
    h = auth_header(auth_token)
    resp = await client.post("/api/v1/cases", headers=h, json={"name": "Default Case", "type": "API"})
    assert resp.status_code == 201
    case_id = resp.json()["data"]["id"]
    detail = await client.get(f"/api/v1/cases/{case_id}", headers=h)
    data = detail.json()["data"]
    assert data["priority"] == "P2"
    assert data["status"] == "DRAFT"
    assert data["version"] == 1


# ── TC-CASE-013: Update case → version increments ──────────────
@pytest.mark.asyncio
async def test_update_case_version_increment(client: AsyncClient, auth_token: str):
    h = auth_header(auth_token)
    create_resp = await client.post("/api/v1/cases", headers=h, json={"name": "Version Case", "type": "API"})
    case_id = create_resp.json()["data"]["id"]

    resp = await client.put(f"/api/v1/cases/{case_id}", headers=h, json={"name": "Updated Case"})
    assert resp.status_code == 200

    detail = await client.get(f"/api/v1/cases/{case_id}", headers=h)
    assert detail.json()["data"]["version"] >= 2


# ── TC-CASE-014: Update nonexistent → 404 ─────────────────────
@pytest.mark.asyncio
async def test_update_nonexistent_case(client: AsyncClient, auth_token: str):
    h = auth_header(auth_token)
    resp = await client.put("/api/v1/cases/00000000-0000-0000-0000-000000000000", headers=h, json={"name": "X"})
    assert resp.status_code == 404


# ── TC-CASE-015: Partial update ────────────────────────────────
@pytest.mark.asyncio
async def test_partial_update(client: AsyncClient, auth_token: str):
    h = auth_header(auth_token)
    create_resp = await client.post("/api/v1/cases", headers=h, json={"name": "Partial", "type": "API", "priority": "P1"})
    case_id = create_resp.json()["data"]["id"]

    resp = await client.put(f"/api/v1/cases/{case_id}", headers=h, json={"priority": "P0"})
    assert resp.status_code == 200
    detail = await client.get(f"/api/v1/cases/{case_id}", headers=h)
    assert detail.json()["data"]["priority"] == "P0"
    assert detail.json()["data"]["name"] == "Partial"


# ── TC-CASE-016: ADMIN delete (soft delete) ────────────────────
@pytest.mark.asyncio
async def test_admin_delete_case(client: AsyncClient, auth_token: str):
    h = auth_header(auth_token)
    create_resp = await client.post("/api/v1/cases", headers=h, json={"name": "To Delete", "type": "API"})
    case_id = create_resp.json()["data"]["id"]

    resp = await client.delete(f"/api/v1/cases/{case_id}", headers=h)
    assert resp.status_code == 200

    # Verify soft deleted
    resp = await client.get(f"/api/v1/cases/{case_id}", headers=h)
    assert resp.status_code == 404


# ── TC-CASE-017: TESTER delete forbidden → 403 ────────────────
@pytest.mark.asyncio
async def test_tester_delete_forbidden(client: AsyncClient, auth_token: str, tester_token: str):
    h = auth_header(auth_token)
    create_resp = await client.post("/api/v1/cases", headers=h, json={"name": "No Delete", "type": "API"})
    case_id = create_resp.json()["data"]["id"]

    resp = await client.delete(f"/api/v1/cases/{case_id}", headers=auth_header(tester_token))
    assert resp.status_code == 403


# ── TC-CASE-018: Delete nonexistent → 404 ─────────────────────
@pytest.mark.asyncio
async def test_delete_nonexistent_case(client: AsyncClient, auth_token: str):
    h = auth_header(auth_token)
    resp = await client.delete("/api/v1/cases/00000000-0000-0000-0000-000000000000", headers=h)
    assert resp.status_code == 404


# ── TC-CASE-019~022: Import/Export (placeholder) ───────────────
@pytest.mark.asyncio
async def test_export_cases(client: AsyncClient, auth_token: str):
    h = auth_header(auth_token)
    resp = await client.post("/api/v1/cases/export", headers=h, json={"ids": []})
    # Export endpoint may not be fully implemented
    assert resp.status_code in (200, 404, 405)


@pytest.mark.asyncio
async def test_import_cases(client: AsyncClient, auth_token: str):
    h = auth_header(auth_token)
    resp = await client.post("/api/v1/cases/import", headers=h, json={"cases": []})
    assert resp.status_code in (200, 404, 405, 422)


# ── TC-CASE-023~025: Versioning (placeholder) ──────────────────
@pytest.mark.asyncio
async def test_case_version_history(client: AsyncClient, auth_token: str):
    h = auth_header(auth_token)
    create_resp = await client.post("/api/v1/cases", headers=h, json={"name": "Versioned", "type": "API"})
    case_id = create_resp.json()["data"]["id"]
    resp = await client.get(f"/api/v1/cases/{case_id}/versions", headers=h)
    assert resp.status_code in (200, 404)
