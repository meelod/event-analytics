from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class VisualizationCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    nl_question: str
    generated_sql: str
    result_data: list[dict[str, Any]]
    chart_config: dict[str, Any]


class VisualizationOut(BaseModel):
    id: str
    org_id: str
    title: str
    nl_question: str
    generated_sql: str
    result_data: list[dict[str, Any]]
    chart_config: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class VisualizationListItem(BaseModel):
    id: str
    title: str
    nl_question: str
    chart_type: str | None = None
    created_at: datetime
