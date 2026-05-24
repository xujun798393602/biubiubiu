from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select, text, update

from app.core.config import settings
from app.core.database import get_engine, Base, get_session_factory
from app.core.security import hash_password
from app.models.user import User, Role, UserRole
from app.models.test_case import CaseFolder, TestCase


async def seed_default_admin():
    """Create default admin user and role if not exists."""
    async with get_session_factory()() as session:
        # Ensure ADMIN role
        role = (await session.execute(select(Role).where(Role.code == "ADMIN"))).scalar_one_or_none()
        if not role:
            role = Role(code="ADMIN", name="管理员", description="系统管理员", permissions=["*"])
            session.add(role)
            await session.flush()

        # Ensure admin user
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

        await session.commit()


async def cleanup_empty_text_fields():
    """Fix records that have literal '' stored as text instead of empty string."""
    async with get_session_factory()() as session:
        for col in ("description", "preconditions", "postconditions", "expected_result", "api_body", "ui_script"):
            await session.execute(
                update(TestCase).where(getattr(TestCase, col) == "''").values({col: ""})
            )
        await session.commit()


async def ensure_default_folder():
    """Create default folder and assign unmapped cases to it."""
    async with get_session_factory()() as session:
        # Check if default folder exists
        default_folder = (await session.execute(
            select(CaseFolder).where(CaseFolder.name == "默认文件夹", CaseFolder.deleted_at.is_(None))
        )).scalar_one_or_none()

        if not default_folder:
            # Get any admin user as creator
            admin = (await session.execute(select(User).limit(1))).scalar_one_or_none()
            if not admin:
                return
            default_folder = CaseFolder(name="默认文件夹", creator_id=admin.id)
            session.add(default_folder)
            await session.flush()

        # Assign all unmapped cases to default folder
        await session.execute(
            update(TestCase)
            .where(TestCase.folder_id.is_(None), TestCase.deleted_at.is_(None))
            .values(folder_id=default_folder.id)
        )
        await session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    eng = get_engine()
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Add missing columns for existing tables (create_all only creates tables, not alter)
        await conn.execute(text("ALTER TABLE IF EXISTS test_cases ADD COLUMN IF NOT EXISTS perf_script TEXT"))
        await conn.execute(text("ALTER TABLE IF EXISTS tasks ADD COLUMN IF NOT EXISTS skipped_count INTEGER NOT NULL DEFAULT 0"))
    await seed_default_admin()
    await ensure_default_folder()
    await cleanup_empty_text_fields()
    yield
    # Shutdown
    from app.services.recording_manager import recording_manager
    await recording_manager.shutdown()
    await eng.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    print(f"[ERROR] {request.method} {request.url.path}: {type(exc).__name__}: {exc}")
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"code": -1, "message": f"服务器内部错误: {type(exc).__name__}: {exc}", "error_code": "INTERNAL_ERROR"},
    )


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": settings.APP_VERSION}


@app.get("/ready")
async def readiness_check():
    return {"status": "ready"}


# Register routers
from app.api.v1.endpoints import auth, cases, tasks, results, nodes, system, record_ws

app.include_router(auth.router, prefix=settings.API_V1_PREFIX + "/auth", tags=["认证"])
app.include_router(cases.router, prefix=settings.API_V1_PREFIX + "/cases", tags=["用例管理"])
app.include_router(tasks.router, prefix=settings.API_V1_PREFIX + "/tasks", tags=["任务管理"])
app.include_router(results.router, prefix=settings.API_V1_PREFIX + "/results", tags=["测试结果"])
app.include_router(nodes.router, prefix=settings.API_V1_PREFIX + "/nodes", tags=["节点管理"])
app.include_router(system.router, prefix=settings.API_V1_PREFIX + "/system", tags=["系统管理"])
app.include_router(record_ws.router, prefix=settings.API_V1_PREFIX, tags=["录制"])
