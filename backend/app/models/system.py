"""SystemLog, Notification, and SystemConfig models."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel
from app.models.enums import OperationType, ResourceType


class SystemLog(BaseModel):
    __tablename__ = "system_logs"

    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, comment="操作人")
    operation: Mapped[OperationType] = mapped_column(String(16), nullable=False, comment="操作类型")
    resource_type: Mapped[ResourceType] = mapped_column(String(16), nullable=False, comment="资源类型")
    resource_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="资源 ID")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, server_default="''", comment="操作描述")
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True, comment="IP 地址")
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True, server_default=text("'{}'::jsonb"), comment="关联数据")

    __table_args__ = (
        Index("idx_system_logs_user_created", "user_id", "created_at"),
        Index("idx_system_logs_operation", "operation"),
        Index("idx_system_logs_resource", "resource_type", "resource_id"),
        Index("idx_system_logs_deleted_at", "deleted_at"),
        {"comment": "系统日志表"},
    )


class Notification(BaseModel):
    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, comment="接收人")
    title: Mapped[str] = mapped_column(String(256), nullable=False, comment="通知标题")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="通知内容")
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="是否已读")
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="阅读时间")

    __table_args__ = (
        Index("idx_notifications_user_read_created", "user_id", "is_read", "created_at"),
        Index("idx_notifications_deleted_at", "deleted_at"),
        {"comment": "通知表"},
    )


class SystemConfig(BaseModel):
    __tablename__ = "system_configs"

    key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, comment="配置键")
    value: Mapped[str] = mapped_column(Text, nullable=False, comment="配置值")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, server_default="''", comment="配置项说明")

    __table_args__ = (
        Index("idx_system_configs_deleted_at", "deleted_at"),
        {"comment": "系统配置表"},
    )
