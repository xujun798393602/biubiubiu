"""Authentication API endpoints."""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.redis import redis_client
from app.core.security import (
    blacklist_token,
    create_access_token,
    decode_token,
    get_current_user,
    hash_password,
    security_scheme,
    verify_password,
)
from app.models.enums import OperationType, ResourceType
from app.models.system import SystemLog
from app.models.user import User, Role
from app.models.user import UserRole
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    ResetPasswordRequest,
    UserInfo,
    VerifyCodeRequest,
)
from app.schemas.common import ResponseModel

router = APIRouter()

LOGIN_FAIL_KEY = "login_fail:{username}"
VERIFICATION_CODE_KEY = "verify_code:{username}"
VERIFICATION_CODE_TTL = 300


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/login", response_model=ResponseModel)
async def login(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    # Check lock
    fail_count = await redis_client.get(LOGIN_FAIL_KEY.format(username=body.username))
    if fail_count and int(fail_count) >= settings.LOGIN_MAX_FAILURES:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail={"code": "ACCOUNT_LOCKED", "message": f"账号已锁定，请 {settings.LOGIN_LOCK_DURATION_SECONDS // 60} 分钟后重试"},
        )

    # Find user
    result = await db.execute(select(User).where(User.username == body.username, User.deleted_at.is_(None)))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        await redis_client.incr(LOGIN_FAIL_KEY.format(username=body.username))
        await redis_client.expire(LOGIN_FAIL_KEY.format(username=body.username), settings.LOGIN_LOCK_DURATION_SECONDS)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_CREDENTIALS", "message": "用户名或密码错误"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "ACCOUNT_DISABLED", "message": "账号已禁用"},
        )

    # Clear fail count
    await redis_client.delete(LOGIN_FAIL_KEY.format(username=body.username))

    # Update last login
    user.last_login_at = datetime.now(timezone.utc)
    user.last_login_ip = _client_ip(request)
    user.login_fail_count = 0

    # Create token
    token = create_access_token({"sub": str(user.id), "username": user.username})

    # Get role
    role_code = user.roles[0].code if user.roles else "USER"
    permissions = []
    for role in user.roles:
        permissions.extend(role.permissions)

    # Log
    db.add(SystemLog(
        user_id=user.id,
        operation=OperationType.LOGIN,
        resource_type=ResourceType.USER,
        resource_id=str(user.id),
        description=f"用户 {user.username} 登录成功",
        ip_address=_client_ip(request),
    ))
    await db.commit()

    return ResponseModel(data={
        "token": token,
        "user": {
            "id": str(user.id),
            "username": user.username,
            "role": role_code,
            "permissions": permissions,
        }
    })


@router.post("/register", response_model=ResponseModel, status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check username uniqueness
    existing = await db.execute(select(User).where(User.username == body.username, User.deleted_at.is_(None)))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "USERNAME_EXISTS", "message": "用户名已存在"},
        )

    # Check email uniqueness
    existing = await db.execute(select(User).where(User.email == body.email, User.deleted_at.is_(None)))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "EMAIL_EXISTS", "message": "邮箱已被注册"},
        )

    # Create user
    user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        email=body.email,
        real_name=body.real_name,
        is_active=True,
    )
    db.add(user)
    await db.flush()

    # Assign default TESTER role
    result = await db.execute(select(Role).where(Role.code == "TESTER", Role.deleted_at.is_(None)))
    tester_role = result.scalar_one_or_none()
    if not tester_role:
        tester_role = Role(code="TESTER", name="测试人员", description="普通测试人员", permissions=["case:*", "task:*", "result:read"])
        db.add(tester_role)
        await db.flush()

    db.add(UserRole(user_id=user.id, role_id=tester_role.id))
    await db.commit()

    return ResponseModel(message="注册成功，请登录")


@router.post("/logout", response_model=ResponseModel)
async def logout(
    credentials=Depends(security_scheme),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await blacklist_token(credentials.credentials)
    db.add(SystemLog(
        user_id=current_user.id,
        operation=OperationType.LOGOUT,
        resource_type=ResourceType.USER,
        resource_id=str(current_user.id),
        description=f"用户 {current_user.username} 登出",
    ))
    await db.commit()
    return ResponseModel(message="登出成功")


@router.post("/refresh-token", response_model=ResponseModel)
async def refresh_token(current_user: User = Depends(get_current_user)):
    token = create_access_token({"sub": str(current_user.id), "username": current_user.username})
    return ResponseModel(data={"token": token})


@router.get("/me", response_model=ResponseModel)
async def get_me(current_user: User = Depends(get_current_user)):
    role_code = current_user.roles[0].code if current_user.roles else "USER"
    permissions = []
    for role in current_user.roles:
        permissions.extend(role.permissions)
    return ResponseModel(data={
        "id": str(current_user.id),
        "username": current_user.username,
        "role": role_code,
        "permissions": permissions,
    })


@router.post("/forgot-password", response_model=ResponseModel)
async def forgot_password(body: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    import random
    code = f"{random.randint(100000, 999999)}"
    await redis_client.setex(VERIFICATION_CODE_KEY.format(username=body.username), VERIFICATION_CODE_TTL, code)
    return ResponseModel(message="验证码已发送", data={"code": code})


@router.post("/verify-code", response_model=ResponseModel)
async def verify_code(body: VerifyCodeRequest):
    stored = await redis_client.get(VERIFICATION_CODE_KEY.format(username=body.username))
    if not stored or stored != body.code:
        raise HTTPException(status_code=400, detail={"code": "INVALID_CODE", "message": "验证码错误或已过期"})
    return ResponseModel(message="验证码正确")


@router.post("/reset-password", response_model=ResponseModel)
async def reset_password(body: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    stored = await redis_client.get(VERIFICATION_CODE_KEY.format(username=body.username))
    if not stored or stored != body.code:
        raise HTTPException(status_code=400, detail={"code": "INVALID_CODE", "message": "验证码错误或已过期"})

    result = await db.execute(select(User).where(User.username == body.username, User.deleted_at.is_(None)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail={"code": "USER_NOT_FOUND", "message": "用户不存在"})

    user.password_hash = hash_password(body.new_password)
    await redis_client.delete(VERIFICATION_CODE_KEY.format(username=body.username))
    await db.commit()
    return ResponseModel(message="密码重置成功")
