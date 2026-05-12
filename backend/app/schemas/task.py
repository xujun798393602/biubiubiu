from typing import Optional, List
from pydantic import BaseModel, Field
from app.schemas.common import ItemBase


class TaskCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    description: Optional[str] = None
    priority: str = "MEDIUM"
    execute_type: str = "IMMEDIATE"
    schedule_cron: Optional[str] = None
    case_ids: List[str] = Field(..., min_length=1, max_length=100)


class TaskUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None


class TaskCaseInfo(BaseModel):
    case_id: str
    case_name: str
    case_type: str
    sort_order: int


class TaskItem(ItemBase):
    id: str
    name: str
    status: str
    priority: str
    execute_type: str
    creator_id: str
    total_cases: int
    success_count: int
    failed_count: int


class TaskDetail(TaskItem):
    schedule_cron: Optional[str] = None
    cases: List[TaskCaseInfo] = []
