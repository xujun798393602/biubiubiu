from typing import Optional, List, Any
from pydantic import BaseModel
from app.schemas.common import ItemBase


class SystemLogItem(ItemBase):
    id: str
    user_id: Optional[str] = None
    operation: str
    resource_type: str
    resource_id: Optional[str] = None
    description: Optional[str] = None
    created_at: str


class NotificationItem(ItemBase):
    id: str
    title: str
    content: str
    is_read: bool
    created_at: str


class ConfigUpdate(BaseModel):
    key: str
    value: Any
    description: Optional[str] = None
