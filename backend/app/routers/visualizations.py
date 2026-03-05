"""
Saved visualizations CRUD routes.

When a user asks a question on the dashboard and likes the result, they can
save it. This persists:
- The original question ("Show daily active users")
- The generated SQL
- The query results (snapshot of the data at save time)
- The chart configuration (chart type, axes, colors)

Reloading a saved visualization is instant - it renders from the cached data,
no LLM call or query needed.

All queries filter by org_id (from the session) for multi-tenant isolation.
A user from Org A can never see Org B's saved visualizations.
"""

import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.db.engine import DuckDBManager
from app.dependencies import get_current_org_from_session, get_db
from app.models.organization import Organization
from app.models.visualization import VisualizationCreate, VisualizationListItem, VisualizationOut

router = APIRouter(prefix="/api/v1/visualizations", tags=["visualizations"])


@router.get("", response_model=list[VisualizationListItem])
async def list_visualizations(
    org: Organization = Depends(get_current_org_from_session),
    db: DuckDBManager = Depends(get_db),
):
    """List all saved visualizations for the current org, newest first."""
    rows = db.execute_read(
        "SELECT id, title, nl_question, chart_config, created_at "
        "FROM saved_visualizations WHERE org_id = ? ORDER BY created_at DESC",
        (org.id,),
    )
    result = []
    for row in rows:
        # DuckDB may return JSON as a string or a dict depending on version
        chart_config = row["chart_config"]
        if isinstance(chart_config, str):
            chart_config = json.loads(chart_config)
        result.append(
            VisualizationListItem(
                id=row["id"],
                title=row["title"],
                nl_question=row["nl_question"],
                chart_type=chart_config.get("chart_type") if isinstance(chart_config, dict) else None,
                created_at=row["created_at"],
            )
        )
    return result


@router.post("", response_model=VisualizationOut, status_code=201)
async def save_visualization(
    body: VisualizationCreate,
    org: Organization = Depends(get_current_org_from_session),
    db: DuckDBManager = Depends(get_db),
):
    """Save a visualization. The frontend sends the full query result + chart config."""
    viz_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    await db.execute_write(
        "INSERT INTO saved_visualizations "
        "(id, org_id, title, nl_question, generated_sql, result_data, chart_config, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [(
            viz_id, org.id, body.title, body.nl_question, body.generated_sql,
            # default=str handles datetime objects in the result data
            json.dumps(body.result_data, default=str),
            json.dumps(body.chart_config, default=str),
            now, now,
        )],
    )
    return VisualizationOut(
        id=viz_id, org_id=org.id, title=body.title,
        nl_question=body.nl_question, generated_sql=body.generated_sql,
        result_data=body.result_data, chart_config=body.chart_config,
        created_at=now, updated_at=now,
    )


@router.get("/{viz_id}", response_model=VisualizationOut)
async def get_visualization(
    viz_id: str,
    org: Organization = Depends(get_current_org_from_session),
    db: DuckDBManager = Depends(get_db),
):
    """Get a single visualization. Always filters by org_id for isolation."""
    rows = db.execute_read(
        "SELECT * FROM saved_visualizations WHERE id = ? AND org_id = ?",
        (viz_id, org.id),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Visualization not found")
    row = rows[0]
    # Parse JSON fields if DuckDB returned them as strings
    result_data = row["result_data"]
    chart_config = row["chart_config"]
    if isinstance(result_data, str):
        result_data = json.loads(result_data)
    if isinstance(chart_config, str):
        chart_config = json.loads(chart_config)
    return VisualizationOut(
        id=row["id"], org_id=row["org_id"], title=row["title"],
        nl_question=row["nl_question"], generated_sql=row["generated_sql"],
        result_data=result_data, chart_config=chart_config,
        created_at=row["created_at"], updated_at=row["updated_at"],
    )


@router.delete("/{viz_id}")
async def delete_visualization(
    viz_id: str,
    org: Organization = Depends(get_current_org_from_session),
    db: DuckDBManager = Depends(get_db),
):
    """Delete a visualization. Checks ownership via org_id before deleting."""
    rows = db.execute_read(
        "SELECT id FROM saved_visualizations WHERE id = ? AND org_id = ?",
        (viz_id, org.id),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Visualization not found")
    await db.execute_write(
        "DELETE FROM saved_visualizations WHERE id = ? AND org_id = ?",
        (viz_id, org.id),
    )
    return {"status": "ok"}
