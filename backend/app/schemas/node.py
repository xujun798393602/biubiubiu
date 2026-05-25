from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from app.schemas.common import ItemBase


class NodeCreate(BaseModel):
    name: str = Field(..., max_length=128)
    host: str = Field(..., max_length=256)
    port: int = 8080
    node_type: str = Field("MIXED", description="节点类型: PLAYWRIGHT/LOCUST/MIXED")
    group_id: Optional[str] = None
    max_concurrent: int = 5
    capabilities: Optional[Dict[str, Any]] = None


class NodeAutoRegister(BaseModel):
    """Worker 自动注册请求"""
    name: str = Field(..., max_length=128, description="节点名称")
    host: str = Field(..., max_length=256, description="节点地址")
    port: int = Field(8080, description="节点端口")
    node_type: str = Field("MIXED", description="节点类型: PLAYWRIGHT/LOCUST/MIXED")
    capabilities: Optional[Dict[str, Any]] = Field(None, description="节点能力配置")
    agent_version: Optional[str] = Field(None, description="Agent 版本")


class NodeUpdate(BaseModel):
    name: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    status: Optional[str] = None
    node_type: Optional[str] = None
    group_id: Optional[str] = None
    max_concurrent: Optional[int] = None
    capabilities: Optional[Dict[str, Any]] = None


class NodeItem(ItemBase):
    id: str
    name: str
    host: str
    port: int
    status: str
    node_type: str = "MIXED"
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None
    disk_usage: Optional[float] = None
    current_tasks: int = 0
    max_concurrent: int = 5
    capabilities: Optional[Dict[str, Any]] = None
    agent_version: Optional[str] = None
    last_heartbeat_at: Optional[str] = None


class NodeStats(BaseModel):
    """节点统计信息"""
    total_nodes: int = 0
    online_nodes: int = 0
    offline_nodes: int = 0
    busy_nodes: int = 0
    error_nodes: int = 0
    by_type: Dict[str, int] = Field(default_factory=dict)
    total_tasks_running: int = 0
    total_max_concurrent: int = 0


class NodeScaleRequest(NodeCreate):
    """一键扩容请求"""
    count: int = Field(1, ge=1, le=10, description="扩容数量")


class NodeScaleResponse(BaseModel):
    """扩容响应"""
    created_nodes: List[str] = Field(default_factory=list)
    message: str = ""


class GroupCreate(BaseModel):
    name: str = Field(..., max_length=128)
    description: Optional[str] = None
