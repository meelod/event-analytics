from typing import Any

from pydantic import BaseModel, Field


class NLQueryRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=1000)


class ChartConfig(BaseModel):
    chart_type: str
    title: str
    x_axis: str | None = None
    y_axis: str | None = None
    series: list[dict[str, Any]] = []


class NLQueryResponse(BaseModel):
    question: str
    generated_sql: str
    data: list[dict[str, Any]]
    chart_config: ChartConfig
    row_count: int
    execution_time_ms: float
