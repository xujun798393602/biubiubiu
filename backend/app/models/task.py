"""Task and TaskLog models."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import TaskPriority, TaskStatus


class Task(BaseModel):
    __tablename__ = "tasks"

    name: Mapped[str] = mapped_column(String(256), nullable=False, comment="任务名称")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, server_default="''", comment="任务描述")
    status: Mapped[TaskStatus] = mapped_column(String(16), nullable=False, default=TaskStatus.PENDING, comment="任务状态")
    priority: Mapped[TaskPriority] = mapped_column(String(16), nullable=False, default=TaskPriority.MEDIUM, comment="优先级")
    execute_type: Mapped[str] = mapped_column(String(16), nullable=False, default="IMMEDIATE", comment="执行类型: IMMEDIATE/SCHEDULED")
    schedule_cron: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="定时执行 cron 表达式")
    creator_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, comment="创建人")
    node_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("test_nodes.id"), nullable=True, comment="执行节点")
    total_cases: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="总用例数")
    success_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="通过数")
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="失败数")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="开始时间")
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="完成时间")

    __table_args__ = (
        Index("idx_tasks_status", "status"),
        Index("idx_tasks_priority", "priority"),
        Index("idx_tasks_creator_id", "creator_id"),
        Index("idx_tasks_deleted_at", "deleted_at"),
        {"comment": "测试任务表"},
    )


class TaskLog(BaseModel):
    __tablename__ = "task_logs"

    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False, comment="任务 ID")
    level: Mapped[str] = mapped_column(String(16), nullable=False, default="INFO", comment="日志级别")
    message: Mapped[str] = mapped_column(Text, nullable=False, comment="日志内容")
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="日志时间戳")

    __table_args__ = (
        Index("idx_task_logs_task_id", "task_id"),
        Index("idx_task_logs_deleted_at", "deleted_at"),
        {"comment": "任务日志表"},
    )
