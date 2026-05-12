"""Pytest configuration and fixtures."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create a test-scoped async engine with NullPool to avoid event loop issues."""
    eng = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db(test_engine):
    """Create all tables before tests, drop after."""
    from app.core.database import Base
    import app.models  # noqa: F401

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(autouse=True)
def mock_redis(monkeypatch):
    """Mock redis_client so tests don't need a real Redis server."""
    mock = AsyncMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.setex = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=1)
    mock.incr = AsyncMock(return_value=1)
    mock.expire = AsyncMock(return_value=True)
    mock.exists = AsyncMock(return_value=0)

    # Patch both locations where redis_client is imported
    import app.core.redis
    import app.core.security
    import app.api.v1.endpoints.auth

    monkeypatch.setattr(app.core.redis, "redis_client", mock)
    monkeypatch.setattr(app.core.security, "redis_client", mock)
    monkeypatch.setattr(app.api.v1.endpoints.auth, "redis_client", mock)

    return mock


@pytest_asyncio.fixture
async def client(test_engine):
    """Test client with overridden DB dependency."""
    from app.main import app
    from app.core.database import get_db

    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(autouse=True)
async def seed_admin(test_engine):
    """Seed admin user and role before each test. Always resets password."""
    from app.core.security import hash_password
    from app.models.user import User, Role, UserRole
    from sqlalchemy import select

    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        role = (await session.execute(select(Role).where(Role.code == "ADMIN"))).scalar_one_or_none()
        if not role:
            role = Role(code="ADMIN", name="管理员", description="系统管理员", permissions=["*"])
            session.add(role)
            await session.flush()

        admin = (await session.execute(select(User).where(User.username == "admin"))).scalar_one_or_none()
        if not admin:
            admin = User(
                username="admin",
                password_hash=hash_password("admin@123"),
                email="admin@example.com",
                real_name="管理员",
                is_active=True,
            )
            session.add(admin)
            await session.flush()
            session.add(UserRole(user_id=admin.id, role_id=role.id))
        else:
            # Always reset password to known value (tests may change it)
            admin.password_hash = hash_password("admin@123")
            admin.is_active = True

        await session.commit()


@pytest_asyncio.fixture
async def auth_token(client: AsyncClient) -> str:
    """Login as admin and return JWT token."""
    resp = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin@123"})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    data = resp.json()
    assert data["code"] == 0, f"Login error: {data}"
    return data["data"]["token"]


@pytest_asyncio.fixture
async def tester_token(client: AsyncClient, test_engine) -> str:
    """Create TESTER user, login, return token."""
    from app.core.security import hash_password
    from app.models.user import User, Role, UserRole
    from sqlalchemy import select

    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        role = (await session.execute(select(Role).where(Role.code == "TESTER"))).scalar_one_or_none()
        if not role:
            role = Role(code="TESTER", name="测试人员", description="测试工程师", permissions=["case:*", "task:*", "result:read"])
            session.add(role)
            await session.flush()

        user = (await session.execute(select(User).where(User.username == "tester"))).scalar_one_or_none()
        if not user:
            user = User(
                username="tester",
                password_hash=hash_password("tester@123"),
                email="tester@example.com",
                real_name="测试员",
                is_active=True,
            )
            session.add(user)
            await session.flush()
            session.add(UserRole(user_id=user.id, role_id=role.id))
        await session.commit()

    resp = await client.post("/api/v1/auth/login", json={"username": "tester", "password": "tester@123"})
    assert resp.status_code == 200, f"Tester login failed: {resp.text}"
    return resp.json()["data"]["token"]


@pytest_asyncio.fixture
async def ops_token(client: AsyncClient, test_engine) -> str:
    """Create OPS user, login, return token."""
    from app.core.security import hash_password
    from app.models.user import User, Role, UserRole
    from sqlalchemy import select

    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        role = (await session.execute(select(Role).where(Role.code == "OPS"))).scalar_one_or_none()
        if not role:
            role = Role(code="OPS", name="运维人员", description="运维工程师", permissions=["node:*", "system:read"])
            session.add(role)
            await session.flush()

        user = (await session.execute(select(User).where(User.username == "ops"))).scalar_one_or_none()
        if not user:
            user = User(
                username="ops",
                password_hash=hash_password("ops@12345"),
                email="ops@example.com",
                real_name="运维员",
                is_active=True,
            )
            session.add(user)
            await session.flush()
            session.add(UserRole(user_id=user.id, role_id=role.id))
        await session.commit()

    resp = await client.post("/api/v1/auth/login", json={"username": "ops", "password": "ops@12345"})
    assert resp.status_code == 200, f"OPS login failed: {resp.text}"
    return resp.json()["data"]["token"]


@pytest_asyncio.fixture
async def disabled_user(test_engine):
    """Create a disabled user in DB."""
    from app.core.security import hash_password
    from app.models.user import User, Role, UserRole
    from sqlalchemy import select

    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        role = (await session.execute(select(Role).where(Role.code == "TESTER"))).scalar_one_or_none()
        if not role:
            role = Role(code="TESTER", name="测试人员", description="测试工程师", permissions=["case:*"])
            session.add(role)
            await session.flush()

        user = (await session.execute(select(User).where(User.username == "disabled_user"))).scalar_one_or_none()
        if not user:
            user = User(
                username="disabled_user",
                password_hash=hash_password("disabled@123"),
                email="disabled@example.com",
                real_name="禁用用户",
                is_active=False,
            )
            session.add(user)
            await session.flush()
            session.add(UserRole(user_id=user.id, role_id=role.id))
        await session.commit()
    return user


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
