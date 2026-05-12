"""TestResult and ResultShare models."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import ResultStatus


class TestResult(BaseModel):
    __tablename__ = "test_results"

    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False, comment="任务 ID")
    case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("test_cases.id"), nullable=False, comment="用例 ID")
    task_case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("task_cases.id"), nullable=False, comment="任务用例关联 ID")
    node_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("test_nodes.id"), nullable=True, comment="执行节点 ID")
    status: Mapped[ResultStatus] = mapped_column(String(16), nullable=False, comment="结果状态")
    detail: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"), comment="详细结果")
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="执行耗时（毫秒）")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="开始执行时间")
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="完成时间")

    shares: Mapped[list["ResultShare"]] = relationship(back_populates="test_result", lazy="noload")

    __table_args__ = (
        Index("idx_test_results_task_id", "task_id"),
        Index("idx_test_results_case_id", "case_id"),
        Index("idx_test_results_task_case_id", "task_case_id"),
        Index("idx_test_results_node_id", "node_id"),
        Index("idx_test_results_status", "status"),
        Index("idx_test_results_created_at", "created_at"),
        Index("idx_test_results_task_created", "task_id", "created_at"),
        Index("idx_test_results_deleted_at", "deleted_at"),
        {"comment": "测试结果表"},
    )


class ResultShare(BaseModel):
    __tablename__ = "result_shares"

    result_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("test_results.id"), nullable=False, comment="关联结果 ID")
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False, comment="关联任务 ID")
    creator_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, comment="创建人")
    token: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, comment="分享 token")
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="访问密码哈希")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="过期时间")
    access_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="访问次数")

    test_result: Mapped["TestResult"] = relationship(back_populates="shares", lazy="selectin")

    __table_args__ = (
        Index("idx_result_shares_result_id", "result_id"),
        Index("idx_result_shares_task_id", "task_id"),
        Index("idx_result_shares_expires_at", "expires_at"),
        Index("idx_result_shares_deleted_at", "deleted_at"),
        {"comment": "结果分享表"},
    )
