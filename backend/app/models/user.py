"""User, Role, and UserRole models."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class User(BaseModel):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, comment="登录用户名")
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False, comment="bcrypt 密码哈希")
    email: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True, comment="邮箱地址")
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="手机号")
    real_name: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="真实姓名")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, comment="账号是否启用")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="最后登录时间")
    last_login_ip: Mapped[str | None] = mapped_column(String(45), nullable=True, comment="最后登录 IP")
    login_fail_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="连续登录失败次数")
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="账号锁定截止时间")
    preferences: Mapped[dict | None] = mapped_column(JSONB, nullable=True, server_default=text("'{}'::jsonb"), comment="用户偏好设置")

    roles: Mapped[list["Role"]] = relationship(secondary="user_roles", back_populates="users", lazy="selectin")

    __table_args__ = (Index("idx_users_deleted_at", "deleted_at"), {"comment": "用户表"})


class Role(BaseModel):
    __tablename__ = "roles"

    code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, comment="角色代号")
    name: Mapped[str] = mapped_column(String(64), nullable=False, comment="角色名称")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="角色描述")
    permissions: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"), comment="权限列表")

    users: Mapped[list["User"]] = relationship(secondary="user_roles", back_populates="roles", lazy="selectin")

    __table_args__ = (Index("idx_roles_deleted_at", "deleted_at"), {"comment": "角色表"})


class UserRole(BaseModel):
    __tablename__ = "user_roles"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, comment="用户 ID")
    role_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id"), nullable=False, comment="角色 ID")

    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="user_roles_user_role_unique"),
        Index("idx_user_roles_user_id", "user_id"),
        Index("idx_user_roles_role_id", "role_id"),
        Index("idx_user_roles_deleted_at", "deleted_at"),
        {"comment": "用户角色关联表"},
    )
