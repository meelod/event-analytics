import re

import sqlglot
from sqlglot import exp


class SQLSandboxError(Exception):
    pass


BLOCKED_PATTERNS = [
    r"\bINSERT\b", r"\bUPDATE\b", r"\bDELETE\b", r"\bDROP\b",
    r"\bALTER\b", r"\bCREATE\b", r"\bTRUNCATE\b", r"\bGRANT\b",
    r"\bREVOKE\b", r"\bCOPY\b", r"\bEXPORT\b", r"\bIMPORT\b",
    r"\bATTACH\b", r"\bDETACH\b", r"\bLOAD\b", r"\bINSTALL\b",
    r"\bCALL\b", r"\bPRAGMA\b", r"\bSET\b", r"\bREAD_CSV\b",
    r"\bREAD_PARQUET\b", r"\bREAD_JSON\b", r"\bHTTPFS\b",
    r"\bS3\b", r"\bSECRET\b",
]


def validate_sql(sql: str, org_id: str) -> str:
    """
    Multi-layer SQL validation:
    1. Regex blocklist for dangerous keywords
    2. Parse with sqlglot to ensure it's a SELECT
    3. Verify org_id filter is present
    4. Enforce LIMIT clause
    """
    sql_upper = sql.upper()
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, sql_upper):
            raise SQLSandboxError(f"Blocked SQL pattern detected")

    try:
        parsed = sqlglot.parse(sql, dialect="duckdb")
    except Exception as e:
        raise SQLSandboxError(f"SQL parse error: {e}")

    if len(parsed) != 1:
        raise SQLSandboxError("Exactly one SQL statement allowed")

    statement = parsed[0]
    if not isinstance(statement, exp.Select):
        raise SQLSandboxError("Only SELECT statements are allowed")

    if org_id not in sql:
        raise SQLSandboxError("Query must filter by organization ID")

    if not statement.find(exp.Limit):
        sql = sql.rstrip(";") + " LIMIT 10000"

    return sql
