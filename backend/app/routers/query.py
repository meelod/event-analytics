from fastapi import APIRouter, Depends, HTTPException

from app.db.engine import DuckDBManager
from app.dependencies import get_current_org_from_session, get_db
from app.models.organization import Organization
from app.models.query import NLQueryRequest, NLQueryResponse
from app.services.nl_to_sql import generate_and_execute_query
from app.services.sql_sandbox import SQLSandboxError

router = APIRouter(prefix="/api/v1", tags=["query"])


@router.post("/query", response_model=NLQueryResponse)
async def natural_language_query(
    request: NLQueryRequest,
    org: Organization = Depends(get_current_org_from_session),
    db: DuckDBManager = Depends(get_db),
):
    try:
        result = await generate_and_execute_query(request.question, org.id, db)
        return NLQueryResponse(**result)
    except SQLSandboxError as e:
        raise HTTPException(status_code=400, detail=f"Query safety error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query execution error: {str(e)}")
