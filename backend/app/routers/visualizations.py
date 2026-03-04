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
    rows = db.execute_read(
        "SELECT id, title, nl_question, chart_config, created_at "
        "FROM saved_visualizations WHERE org_id = ? ORDER BY created_at DESC",
        (org.id,),
    )
    result = []
    for row in rows:
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
    viz_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    await db.execute_write(
        "INSERT INTO saved_visualizations "
        "(id, org_id, title, nl_question, generated_sql, result_data, chart_config, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [(
            viz_id, org.id, body.title, body.nl_question, body.generated_sql,
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
    rows = db.execute_read(
        "SELECT * FROM saved_visualizations WHERE id = ? AND org_id = ?",
        (viz_id, org.id),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Visualization not found")
    row = rows[0]
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
