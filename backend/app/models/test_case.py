"""TestCase and related extension models."""

import uuid

from sqlalchemy import ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import BodyType, CaseStatus, CaseType, HttpMethod, Priority


class CaseFolder(BaseModel):
    __tablename__ = "case_folders"

    name: Mapped[str] = mapped_column(String(128), nullable=False, comment="文件夹名称")
    parent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("case_folders.id"), nullable=True, comment="父文件夹 ID")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="排序序号")
    creator_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, comment="创建人")

    __table_args__ = (
        Index("idx_case_folders_parent_id", "parent_id"),
        Index("idx_case_folders_deleted_at", "deleted_at"),
        {"comment": "用例文件夹表"},
    )


class TestCase(BaseModel):
    __tablename__ = "test_cases"

    name: Mapped[str] = mapped_column(String(256), nullable=False, comment="用例名称")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, server_default=text("''"), comment="用例描述")
    type: Mapped[CaseType] = mapped_column(String(16), nullable=False, comment="用例类型")
    status: Mapped[CaseStatus] = mapped_column(String(16), nullable=False, default=CaseStatus.DRAFT, comment="用例状态")
    priority: Mapped[Priority] = mapped_column(String(4), nullable=False, default=Priority.P2, comment="优先级")
    module: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="所属模块")
    tags: Mapped[list | None] = mapped_column(JSONB, nullable=True, comment="标签列表")
    preconditions: Mapped[str | None] = mapped_column(Text, nullable=True, server_default=text("''"), comment="前置条件")
    steps: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"), comment="执行步骤列表")
    postconditions: Mapped[str | None] = mapped_column(Text, nullable=True, server_default=text("''"), comment="后置条件")
    expected_result: Mapped[str | None] = mapped_column(Text, nullable=True, server_default=text("''"), comment="预期结果")
    author: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="用例编写人")
    assertions: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"), comment="断言规则列表")
    creator_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, comment="创建人")
    folder_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("case_folders.id"), nullable=True, comment="所属文件夹 ID")

    # API test fields
    api_url: Mapped[str | None] = mapped_column(String(512), nullable=True, comment="接口 URL")
    api_method: Mapped[HttpMethod | None] = mapped_column(String(10), nullable=True, comment="请求方法")
    api_headers: Mapped[dict | None] = mapped_column(JSONB, nullable=True, server_default=text("'{}'::jsonb"), comment="请求头")
    api_body_type: Mapped[BodyType | None] = mapped_column(String(16), nullable=True, comment="请求体类型")
    api_body: Mapped[str | None] = mapped_column(Text, nullable=True, server_default=text("''"), comment="请求体内容")
    api_timeout: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="接口超时时间(ms)")
    api_assertions: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"), comment="断言规则列表")
    api_dependencies: Mapped[list | None] = mapped_column(JSONB, nullable=True, server_default=text("'[]'::jsonb"), comment="接口依赖配置")

    # UI test fields
    ui_url: Mapped[str | None] = mapped_column(String(512), nullable=True, comment="页面 URL")
    ui_script: Mapped[str | None] = mapped_column(Text, nullable=True, server_default=text("''"), comment="UI 自动化脚本")
    ui_script_type: Mapped[str | None] = mapped_column(String(16), nullable=True, comment="脚本类型: MANUAL/PLAYWRIGHT/SELENIUM")
    ui_steps: Mapped[list | None] = mapped_column(JSONB, nullable=True, comment="UI 操作步骤")

    # Performance test fields
    perf_url: Mapped[str | None] = mapped_column(String(512), nullable=True, comment="压测目标 URL")
    perf_vusers: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="并发用户数")
    perf_spawn_rate: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="每秒启动用户数")
    perf_duration: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="持续时间(秒)")
    perf_assertions: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"), comment="性能断言规则")

    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, comment="版本号")

    __table_args__ = (
        Index("idx_test_cases_type", "type"),
        Index("idx_test_cases_status", "status"),
        Index("idx_test_cases_priority", "priority"),
        Index("idx_test_cases_creator_id", "creator_id"),
        Index("idx_test_cases_folder_id", "folder_id"),
        Index("idx_test_cases_deleted_at", "deleted_at"),
        {"comment": "测试用例表"},
    )


class TaskCase(BaseModel):
    __tablename__ = "task_cases"

    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False, comment="任务 ID")
    case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("test_cases.id"), nullable=False, comment="用例 ID")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="执行顺序")

    __table_args__ = (
        UniqueConstraint("task_id", "case_id", name="task_cases_task_case_unique"),
        Index("idx_task_cases_task_id", "task_id"),
        Index("idx_task_cases_case_id", "case_id"),
        Index("idx_task_cases_deleted_at", "deleted_at"),
        {"comment": "任务用例关联表"},
    )
