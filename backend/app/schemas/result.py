from typing import Optional, List, Any
from pydantic import BaseModel


class ResultItem(BaseModel):
    id: str
    task_id: str
    case_id: str
    caseName: str = ""
    caseType: str = ""
    status: str
    duration: float = 0
    startedAt: Optional[str] = None
    finishedAt: Optional[str] = None

    class Config:
        from_attributes = True


class ResultOverview(BaseModel):
    totalCases: int = 0
    successCount: int = 0
    failedCount: int = 0
    successRate: float = 0


class ResultDetail(BaseModel):
    id: str
    task_id: str
    case_id: str
    status: str
    detail: dict = {}
    expected: Any = None
    actual: Any = None
    duration_ms: int = 0


class ShareCreate(BaseModel):
    expires_in_hours: Optional[int] = 168  # 7 days default
    password: Optional[str] = None
