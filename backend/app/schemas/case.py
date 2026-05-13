from typing import Literal, Optional, List, Any
from pydantic import BaseModel, Field
from app.schemas.common import ItemBase


# Folder schemas
class FolderCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    parent_id: Optional[str] = None


class FolderUpdate(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[str] = None


class FolderItem(ItemBase):
    id: str
    name: str
    parent_id: Optional[str] = None
    sort_order: int = 0
    creator_id: str
    case_count: int = 0


class FolderTreeItem(ItemBase):
    id: str
    name: str
    parent_id: Optional[str] = None
    sort_order: int = 0
    case_count: int = 0
    children: List["FolderTreeItem"] = []


# Case schemas
class CaseCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    description: Optional[str] = None
    type: Literal["UI", "API", "PERFORMANCE"]
    priority: str = "P2"
    module: Optional[str] = None
    folder_id: Optional[str] = None
    tags: Optional[List[str]] = None
    author: Optional[str] = None
    preconditions: Optional[str] = None
    steps: List[dict] = []
    postconditions: Optional[str] = None
    expected_result: Optional[str] = None
    assertions: List[dict] = []

    # UI fields
    ui_url: Optional[str] = None
    ui_script: Optional[str] = None
    ui_script_type: Optional[str] = None

    # API fields
    api_url: Optional[str] = None
    api_method: Optional[str] = None
    api_headers: Optional[dict] = None
    api_body_type: Optional[str] = None
    api_body: Optional[str] = None
    api_timeout: Optional[int] = None
    api_assertions: Optional[List[dict]] = None

    # Performance fields
    perf_url: Optional[str] = None
    perf_vusers: Optional[int] = None
    perf_spawn_rate: Optional[int] = None
    perf_duration: Optional[int] = None
    perf_assertions: Optional[List[dict]] = None


class CaseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    module: Optional[str] = None
    folder_id: Optional[str] = None
    tags: Optional[List[str]] = None
    author: Optional[str] = None
    preconditions: Optional[str] = None
    steps: Optional[List[dict]] = None
    postconditions: Optional[str] = None
    expected_result: Optional[str] = None
    assertions: Optional[List[dict]] = None

    # UI fields
    ui_url: Optional[str] = None
    ui_script: Optional[str] = None
    ui_script_type: Optional[str] = None

    # API fields
    api_url: Optional[str] = None
    api_method: Optional[str] = None
    api_headers: Optional[dict] = None
    api_body_type: Optional[str] = None
    api_body: Optional[str] = None
    api_timeout: Optional[int] = None
    api_assertions: Optional[List[dict]] = None

    # Performance fields
    perf_url: Optional[str] = None
    perf_vusers: Optional[int] = None
    perf_spawn_rate: Optional[int] = None
    perf_duration: Optional[int] = None
    perf_assertions: Optional[List[dict]] = None


class CaseItem(ItemBase):
    id: str
    name: str
    type: str
    status: str
    priority: str
    module: Optional[str] = None
    folder_id: Optional[str] = None
    tags: Optional[List[str]] = None
    author: Optional[str] = None
    preconditions: Optional[str] = None
    steps: Optional[List[dict]] = None
    postconditions: Optional[str] = None
    expected_result: Optional[str] = None
    creator_id: str
    version: int

    # UI fields
    ui_url: Optional[str] = None
    ui_script: Optional[str] = None
    ui_script_type: Optional[str] = None

    # API fields
    api_url: Optional[str] = None
    api_method: Optional[str] = None
    api_headers: Optional[dict] = None
    api_body_type: Optional[str] = None
    api_body: Optional[str] = None
    api_timeout: Optional[int] = None
    api_assertions: Optional[List[dict]] = None

    # Performance fields
    perf_url: Optional[str] = None
    perf_vusers: Optional[int] = None
    perf_spawn_rate: Optional[int] = None
    perf_duration: Optional[int] = None
    perf_assertions: Optional[List[dict]] = None
