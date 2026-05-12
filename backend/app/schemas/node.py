from typing import Optional, List
from pydantic import BaseModel, Field
from app.schemas.common import ItemBase


class NodeCreate(BaseModel):
    name: str = Field(..., max_length=128)
    host: str = Field(..., max_length=256)
    port: int = 8080
    group_id: Optional[str] = None
    max_concurrent: int = 5


class NodeUpdate(BaseModel):
    name: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    status: Optional[str] = None
    group_id: Optional[str] = None
    max_concurrent: Optional[int] = None


class NodeItem(ItemBase):
    id: str
    name: str
    host: str
    port: int
    status: str
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None
    current_tasks: int = 0


class GroupCreate(BaseModel):
    name: str = Field(..., max_length=128)
    description: Optional[str] = None
