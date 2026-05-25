"""Admin user management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, hash_password, require_roles
from app.models.enums import OperationType, ResourceType
from app.models.system import SystemLog
from app.models.user import User, Role, UserRole
from app.schemas.common import ItemBase, ResponseModel
from typing import Optional
from pydantic import BaseModel, Field


# --- Schemas ---

class UserListItem(ItemBase):
    id: str
    username: str
    email: Optional[str] = None
    real_name: Optional[str] = None
    is_active: bool
    last_login_at: Optional[str] = None
    role: str = ""


class UserCreateRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=8, max_length=128)
    email: str = Field(..., max_length=128)
    real_name: Optional[str] = Field(None, max_length=128)
    role_code: str = Field("TESTER", description="角色代号: ADMIN/TESTER/OPS")


class ResetPasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=8, max_length=128)


class ToggleActiveRequest(BaseModel):
    is_active: bool


# --- Router ---

router = APIRouter()


@router.get("", response_model=ResponseModel)
async def list_users(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    keyword: str = Query(None, description="搜索用户名/邮箱/真实姓名"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN")),
):
    query = select(User).where(User.deleted_at.is_(None))
    count_query = select(func.count()).select_from(User).where(User.deleted_at.is_(None))

    if keyword:
        like = f"%{keyword}%"
        cond = User.username.ilike(like) | User.email.ilike(like) | User.real_name.ilike(like)
        query = query.where(cond)
        count_query = count_query.where(cond)

    total = (await db.execute(count_query)).scalar()
    items = (await db.execute(
        query.order_by(User.created_at.desc()).offset((page - 1) * pageSize).limit(pageSize)
    )).scalars().all()

    result = []
    for u in items:
        role_code = u.roles[0].code if u.roles else ""
        result.append(UserListItem(
            id=str(u.id),
            username=u.username,
            email=u.email,
            real_name=u.real_name,
            is_active=u.is_active,
            last_login_at=u.last_login_at.isoformat() if u.last_login_at else None,
            role=role_code,
            created_at=u.created_at.isoformat() if u.created_at else None,
        ))

    return ResponseModel(data={
        "list": result,
        "pagination": {"page": page, "pageSize": pageSize, "total": total, "totalPages": (total + pageSize - 1) // pageSize},
    })


@router.post("", response_model=ResponseModel, status_code=201)
async def create_user(
    body: UserCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN")),
):
    # Check username
    existing = await db.execute(select(User).where(User.username == body.username, User.deleted_at.is_(None)))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"code": "USERNAME_EXISTS", "message": "用户名已存在"})

    # Check email
    existing = await db.execute(select(User).where(User.email == body.email, User.deleted_at.is_(None)))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"code": "EMAIL_EXISTS", "message": "邮箱已被注册"})

    # Find role
    role_result = await db.execute(select(Role).where(Role.code == body.role_code, Role.deleted_at.is_(None)))
    role = role_result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": "ROLE_NOT_FOUND", "message": f"角色 {body.role_code} 不存在"})

    user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        email=body.email,
        real_name=body.real_name,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    db.add(UserRole(user_id=user.id, role_id=role.id))

    db.add(SystemLog(
        user_id=current_user.id,
        operation=OperationType.CREATE,
        resource_type=ResourceType.USER,
        resource_id=str(user.id),
        description=f"管理员创建用户 {user.username}",
    ))
    await db.commit()

    return ResponseModel(message="用户创建成功", data={"id": str(user.id)})


@router.put("/{user_id}/reset-password", response_model=ResponseModel)
async def reset_user_password(
    user_id: str,
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN")),
):
    result = await db.execute(select(User).where(User.id == user_id, User.deleted_at.is_(None)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail={"code": "USER_NOT_FOUND", "message": "用户不存在"})

    user.password_hash = hash_password(body.new_password)
    user.login_fail_count = 0

    db.add(SystemLog(
        user_id=current_user.id,
        operation=OperationType.UPDATE,
        resource_type=ResourceType.USER,
        resource_id=str(user.id),
        description=f"管理员重置用户 {user.username} 的密码",
    ))
    await db.commit()

    return ResponseModel(message="密码重置成功")


@router.put("/{user_id}/toggle-active", response_model=ResponseModel)
async def toggle_user_active(
    user_id: str,
    body: ToggleActiveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN")),
):
    if str(current_user.id) == user_id:
        raise HTTPException(status_code=400, detail={"code": "CANNOT_DISABLE_SELF", "message": "不能禁用自己的账号"})

    result = await db.execute(select(User).where(User.id == user_id, User.deleted_at.is_(None)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail={"code": "USER_NOT_FOUND", "message": "用户不存在"})

    user.is_active = body.is_active
    action = "启用" if body.is_active else "禁用"

    db.add(SystemLog(
        user_id=current_user.id,
        operation=OperationType.UPDATE,
        resource_type=ResourceType.USER,
        resource_id=str(user.id),
        description=f"管理员{action}用户 {user.username}",
    ))
    await db.commit()

    return ResponseModel(message=f"用户已{action}")
