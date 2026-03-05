"""
Natural language query route.

POST /api/v1/query accepts a question string, runs the full NL-to-SQL pipeline,
and returns the generated SQL, query results, and chart configuration.

Uses session auth (not API key) because this is a dashboard feature.
The org_id is resolved from the session cookie automatically.

Error handling separates sandbox errors (400 - the SQL was unsafe) from
execution errors (500 - something crashed). This helps the frontend show
appropriate error messages.
"""

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
        # 400: The LLM generated unsafe SQL (blocked by sandbox)
        raise HTTPException(status_code=400, detail=f"Query safety error: {e}")
    except Exception as e:
        # 500: Something else went wrong (LLM API error, DuckDB error, etc.)
        raise HTTPException(status_code=500, detail=f"Query execution error: {str(e)}")
