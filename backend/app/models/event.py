from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class EventIn(BaseModel):
    event: str = Field(..., min_length=1, max_length=255)
    distinct_id: str = Field(..., min_length=1, max_length=255)
    timestamp: datetime | None = None
    properties: dict[str, Any] = Field(default_factory=dict)

    @field_validator("properties")
    @classmethod
    def validate_properties(cls, v: dict) -> dict:
        if len(v) > 50:
            raise ValueError("Maximum 50 properties per event")
        return v


class EventBatchIn(BaseModel):
    events: list[EventIn] = Field(..., min_length=1, max_length=1000)


class EventResponse(BaseModel):
    status: str = "ok"
    event_id: str


class BatchResponse(BaseModel):
    status: str = "ok"
    accepted: int
    errors: list[dict[str, Any]] = []
