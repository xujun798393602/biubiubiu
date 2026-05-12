from datetime import datetime
from typing import Any, Generic, TypeVar, Optional, List
from uuid import UUID
from pydantic import BaseModel, ConfigDict, model_validator

T = TypeVar("T")


class ResponseModel(BaseModel):
    code: int = 0
    message: str = "success"
    data: Any = None


class PaginatedResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: dict = None


class PaginationParams(BaseModel):
    page: int = 1
    pageSize: int = 20


class ItemBase(BaseModel):
    """Base for response item schemas — coerces UUID/datetime fields to str automatically."""
    model_config = ConfigDict(from_attributes=True)

    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_types(cls, values):
        if hasattr(values, "__dict__"):
            # Convert to dict to avoid mutating the SQLAlchemy model instance
            data = {}
            for field in cls.model_fields:
                val = getattr(values, field, None)
                if isinstance(val, UUID):
                    data[field] = str(val)
                elif isinstance(val, datetime):
                    data[field] = val.isoformat()
                else:
                    data[field] = val
            return data
        if isinstance(values, dict):
            for k, v in values.items():
                if isinstance(v, UUID):
                    values[k] = str(v)
                elif isinstance(v, datetime):
                    values[k] = v.isoformat()
        return values
