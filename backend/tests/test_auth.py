"""Authentication API tests — 25 E2E cases."""

import pytest
from httpx import AsyncClient
from tests.conftest import auth_header


# ── TC-AUTH-001: Normal login ──────────────────────────────────
@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    resp = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin@123"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert "token" in data["data"]
    assert data["data"]["user"]["username"] == "admin"


# ── TC-AUTH-002: Wrong password ────────────────────────────────
@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    resp = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrongpassword"})
    assert resp.status_code == 401
    data = resp.json()
    assert data["detail"]["code"] == "INVALID_CREDENTIALS"


# ── TC-AUTH-003: User not found (anti-enumeration) ─────────────
@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    resp = await client.post("/api/v1/auth/login", json={"username": "nobody", "password": "12345678"})
    assert resp.status_code == 401
    data = resp.json()
    assert data["detail"]["code"] == "INVALID_CREDENTIALS"


# ── TC-AUTH-004: Disabled account ──────────────────────────────
@pytest.mark.asyncio
async def test_login_disabled_account(client: AsyncClient, disabled_user):
    resp = await client.post("/api/v1/auth/login", json={"username": "disabled_user", "password": "disabled@123"})
    assert resp.status_code == 403
    data = resp.json()
    assert data["detail"]["code"] == "ACCOUNT_DISABLED"


# ── TC-AUTH-005: Account lockout after 5 failures ──────────────
@pytest.mark.asyncio
async def test_login_account_lockout(client: AsyncClient, mock_redis):
    # Simulate 5 failures already recorded
    mock_redis.get = AsyncMock(return_value="5")
    resp = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin@123"})
    assert resp.status_code == 423
    data = resp.json()
    assert data["detail"]["code"] == "ACCOUNT_LOCKED"


# ── TC-AUTH-006/007: Empty username/password → 422 ─────────────
@pytest.mark.asyncio
async def test_login_empty_username(client: AsyncClient):
    resp = await client.post("/api/v1/auth/login", json={"username": "", "password": "12345678"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login_empty_password(client: AsyncClient):
    resp = await client.post("/api/v1/auth/login", json={"username": "admin", "password": ""})
    assert resp.status_code == 422


# ── TC-AUTH-008: Logout ────────────────────────────────────────
@pytest.mark.asyncio
async def test_logout(client: AsyncClient, auth_token: str):
    resp = await client.post("/api/v1/auth/logout", headers=auth_header(auth_token))
    assert resp.status_code == 200


# ── TC-AUTH-009: Token revoked after logout ────────────────────
@pytest.mark.asyncio
async def test_token_revoked_after_logout(client: AsyncClient, auth_token: str, mock_redis):
    # Simulate token blacklisted
    mock_redis.exists = AsyncMock(return_value=1)
    resp = await client.get("/api/v1/auth/me", headers=auth_header(auth_token))
    assert resp.status_code == 401
    data = resp.json()
    assert data["detail"]["code"] == "TOKEN_REVOKED"


# ── TC-AUTH-010: Refresh token ─────────────────────────────────
@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient, auth_token: str):
    resp = await client.post("/api/v1/auth/refresh-token", headers=auth_header(auth_token))
    assert resp.status_code == 200
    assert "token" in resp.json()["data"]


# ── TC-AUTH-011: Refresh with invalid token ────────────────────
@pytest.mark.asyncio
async def test_refresh_invalid_token(client: AsyncClient):
    resp = await client.post("/api/v1/auth/refresh-token", headers=auth_header("invalid.token.here"))
    assert resp.status_code == 401


# ── TC-AUTH-012: GET /me returns user info ─────────────────────
@pytest.mark.asyncio
async def test_get_me(client: AsyncClient, auth_token: str):
    resp = await client.get("/api/v1/auth/me", headers=auth_header(auth_token))
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["username"] == "admin"
    assert "role" in data
    assert "permissions" in data


# ── TC-AUTH-013: GET /me without token → 401 ──────────────────
@pytest.mark.asyncio
async def test_get_me_no_token(client: AsyncClient):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


# ── TC-AUTH-014~018: Password reset flow ───────────────────────
@pytest.mark.asyncio
async def test_forgot_password(client: AsyncClient):
    resp = await client.post("/api/v1/auth/forgot-password", json={"username": "admin"})
    assert resp.status_code == 200
    assert resp.json()["data"]["code"]


@pytest.mark.asyncio
async def test_verify_code_correct(client: AsyncClient, mock_redis):
    mock_redis.get = AsyncMock(return_value="123456")
    resp = await client.post("/api/v1/auth/verify-code", json={"username": "admin", "code": "123456"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_verify_code_wrong(client: AsyncClient, mock_redis):
    mock_redis.get = AsyncMock(return_value="123456")
    resp = await client.post("/api/v1/auth/verify-code", json={"username": "admin", "code": "000000"})
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "INVALID_CODE"


@pytest.mark.asyncio
async def test_verify_code_expired(client: AsyncClient, mock_redis):
    mock_redis.get = AsyncMock(return_value=None)
    resp = await client.post("/api/v1/auth/verify-code", json={"username": "admin", "code": "123456"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_reset_password(client: AsyncClient, mock_redis, test_engine):
    mock_redis.get = AsyncMock(return_value="123456")
    resp = await client.post("/api/v1/auth/reset-password", json={
        "username": "admin", "code": "123456", "new_password": "newpass@123"
    })
    assert resp.status_code == 200


# ── TC-AUTH-019: ADMIN full access ─────────────────────────────
@pytest.mark.asyncio
async def test_admin_full_access(client: AsyncClient, auth_token: str):
    h = auth_header(auth_token)
    # Can create case
    resp = await client.post("/api/v1/cases", headers=h, json={"name": "Admin case", "type": "API"})
    assert resp.status_code == 201
    # Can list nodes
    resp = await client.get("/api/v1/nodes", headers=h)
    assert resp.status_code == 200
    # Can view logs
    resp = await client.get("/api/v1/system/logs", headers=h)
    assert resp.status_code == 200


# ── TC-AUTH-020: TESTER RBAC ───────────────────────────────────
@pytest.mark.asyncio
async def test_tester_rbac(client: AsyncClient, tester_token: str):
    h = auth_header(tester_token)
    # Can create case
    resp = await client.post("/api/v1/cases", headers=h, json={"name": "Tester case", "type": "API"})
    assert resp.status_code == 201
    # Cannot view system logs (requires ADMIN)
    resp = await client.get("/api/v1/system/logs", headers=h)
    assert resp.status_code == 403


# ── TC-AUTH-021/022: OPS RBAC ──────────────────────────────────
@pytest.mark.asyncio
async def test_ops_rbac(client: AsyncClient, ops_token: str):
    h = auth_header(ops_token)
    # Can manage nodes
    resp = await client.post("/api/v1/nodes", headers=h, json={"name": "OPS node", "host": "10.0.0.1", "port": 8080})
    assert resp.status_code == 201
    # Cannot create cases
    resp = await client.post("/api/v1/cases", headers=h, json={"name": "OPS case", "type": "API"})
    assert resp.status_code == 403


# ── TC-AUTH-023: Login audit log ───────────────────────────────
@pytest.mark.asyncio
async def test_login_creates_audit_log(client: AsyncClient, auth_token: str, test_engine):
    from sqlalchemy import select
    from app.models.system import SystemLog
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        logs = (await session.execute(
            select(SystemLog).where(SystemLog.operation == "LOGIN").order_by(SystemLog.created_at.desc())
        )).scalars().all()
        assert len(logs) >= 1


# ── TC-AUTH-024: Password stored as bcrypt ─────────────────────
@pytest.mark.asyncio
async def test_password_bcrypt_format(test_engine):
    from sqlalchemy import select
    from app.models.user import User
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        user = (await session.execute(select(User).where(User.username == "admin"))).scalar_one()
        assert user.password_hash.startswith("$2b$")


# ── TC-AUTH-025: JWT expiry (mock) ─────────────────────────────
@pytest.mark.asyncio
async def test_jwt_expired_token(client: AsyncClient):
    # Create an already-expired token
    from datetime import datetime, timedelta, timezone
    from jose import jwt
    from app.core.config import settings

    expired_payload = {
        "sub": "fake-id",
        "username": "admin",
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
    }
    expired_token = jwt.encode(expired_payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    resp = await client.get("/api/v1/auth/me", headers=auth_header(expired_token))
    assert resp.status_code == 401


# ── Helpers ────────────────────────────────────────────────────
from unittest.mock import AsyncMock
