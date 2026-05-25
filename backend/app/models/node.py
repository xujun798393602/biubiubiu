"""TestNode and NodeGroup models."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import NodeStatus, NodeType


class NodeGroup(BaseModel):
    __tablename__ = "node_groups"

    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, comment="分组名称")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, server_default="''", comment="分组描述")

    nodes: Mapped[list["TestNode"]] = relationship(back_populates="group", lazy="selectin")

    __table_args__ = (Index("idx_node_groups_deleted_at", "deleted_at"), {"comment": "节点分组表"})


class TestNode(BaseModel):
    __tablename__ = "test_nodes"

    name: Mapped[str] = mapped_column(String(128), nullable=False, comment="节点名称")
    host: Mapped[str] = mapped_column(String(256), nullable=False, comment="节点地址")
    port: Mapped[int] = mapped_column(Integer, nullable=False, default=8080, comment="节点端口")
    status: Mapped[NodeStatus] = mapped_column(String(16), nullable=False, default=NodeStatus.OFFLINE, comment="节点状态")
    node_type: Mapped[str] = mapped_column(String(16), nullable=False, default="MIXED", comment="节点类型: PLAYWRIGHT/LOCUST/MIXED")
    group_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("node_groups.id"), nullable=True, comment="所属分组")
    browser_info: Mapped[dict | None] = mapped_column(JSONB, nullable=True, server_default=text("'{}'::jsonb"), comment="浏览器版本信息")
    tool_versions: Mapped[dict | None] = mapped_column(JSONB, nullable=True, server_default=text("'{}'::jsonb"), comment="已安装工具版本")
    capabilities: Mapped[dict | None] = mapped_column(JSONB, nullable=True, server_default=text("'{}'::jsonb"), comment="节点能力配置")
    max_concurrent: Mapped[int] = mapped_column(Integer, nullable=False, default=5, comment="最大并发任务数")
    current_tasks: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="当前任务数")
    agent_version: Mapped[str | None] = mapped_column(String(32), nullable=True, server_default="''", comment="客户端代理版本")
    api_key: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="节点认证密钥")
    cpu_usage: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True, server_default="0.00", comment="CPU 使用率")
    memory_usage: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True, server_default="0.00", comment="内存使用率")
    disk_usage: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True, server_default="0.00", comment="磁盘使用率")
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="最后心跳时间")

    group: Mapped["NodeGroup | None"] = relationship(back_populates="nodes", lazy="selectin")

    __table_args__ = (
        Index("idx_test_nodes_status", "status"),
        Index("idx_test_nodes_group_id", "group_id"),
        Index("idx_test_nodes_deleted_at", "deleted_at"),
        {"comment": "测试节点表"},
    )
