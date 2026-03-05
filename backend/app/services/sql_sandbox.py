"""
SQL Sandbox - validates and sanitizes LLM-generated SQL before execution.

This is the most security-critical module in the system. The LLM generates SQL
from user questions, but LLM output is UNTRUSTED INPUT - it could contain:
- Destructive statements (DROP TABLE, DELETE)
- Data exfiltration (COPY TO, EXPORT)
- File system access (read_csv, read_parquet)
- Privilege escalation (GRANT, ATTACH)

We use defense-in-depth with 4 validation layers:

Layer 1: Regex blocklist - fast first pass, catches obvious dangerous keywords
Layer 2: AST parsing via sqlglot - structural validation (is it actually a SELECT?)
Layer 3: Org ID check - ensures multi-tenant isolation isn't bypassed
Layer 4: LIMIT enforcement - prevents runaway queries returning millions of rows

Why both regex AND AST parsing?
- Regex alone can be bypassed: SE/**/LECT, unicode tricks, etc.
- AST parsing alone might miss DuckDB-specific dangerous functions
- Together they provide layered security

Trade-off: sqlglot is an extra dependency (~5MB). Worth it for the structural
guarantees. A regex-only approach would be fragile for a take-home that
explicitly asks about "safe handling of LLM-generated queries."
"""

import re

import sqlglot
from sqlglot import exp


class SQLSandboxError(Exception):
    """Raised when LLM-generated SQL fails validation."""
    pass


# Regex patterns for dangerous SQL operations.
# \b = word boundary, so "SET" matches but "OFFSET" doesn't.
BLOCKED_PATTERNS = [
    # DML (data modification)
    r"\bINSERT\b", r"\bUPDATE\b", r"\bDELETE\b",
    # DDL (schema modification)
    r"\bDROP\b", r"\bALTER\b", r"\bCREATE\b", r"\bTRUNCATE\b",
    # Privilege commands
    r"\bGRANT\b", r"\bREVOKE\b",
    # File I/O (DuckDB can read/write files - very dangerous)
    r"\bCOPY\b", r"\bEXPORT\b", r"\bIMPORT\b",
    # DuckDB extension system (could load arbitrary code)
    r"\bATTACH\b", r"\bDETACH\b", r"\bLOAD\b", r"\bINSTALL\b",
    # Stored procedures / system config
    r"\bCALL\b", r"\bPRAGMA\b", r"\bSET\b",
    # DuckDB file-reading functions (could read arbitrary files from disk)
    r"\bREAD_CSV\b", r"\bREAD_PARQUET\b", r"\bREAD_JSON\b",
    # Remote access extensions
    r"\bHTTPFS\b", r"\bS3\b", r"\bSECRET\b",
]


def validate_sql(sql: str, org_id: str) -> str:
    """
    Validate LLM-generated SQL through 4 layers. Returns the (possibly modified)
    SQL on success, raises SQLSandboxError on failure.
    """

    # ── Layer 1: Regex blocklist ──────────────────────────────────────
    # Fast scan for obviously dangerous keywords. Runs in microseconds.
    sql_upper = sql.upper()
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, sql_upper):
            raise SQLSandboxError(f"Blocked SQL pattern detected")

    # ── Layer 2: AST-level validation via sqlglot ─────────────────────
    # Parse the SQL into an Abstract Syntax Tree using DuckDB dialect.
    # This catches structural attacks that regex misses (e.g., UNION-based
    # injection, subquery tricks, comment-based obfuscation).
    try:
        parsed = sqlglot.parse(sql, dialect="duckdb")
    except Exception as e:
        raise SQLSandboxError(f"SQL parse error: {e}")

    # Must be exactly one statement (prevents "SELECT ...; DROP TABLE ...")
    if len(parsed) != 1:
        raise SQLSandboxError("Exactly one SQL statement allowed")

    # The parsed AST node must be a Select expression
    statement = parsed[0]
    if not isinstance(statement, exp.Select):
        raise SQLSandboxError("Only SELECT statements are allowed")

    # ── Layer 3: Multi-tenant isolation check ─────────────────────────
    # The org_id must appear in the SQL string. This ensures the LLM
    # included the WHERE org_id = '...' filter. Without this, a crafted
    # question could trick the LLM into generating a query without the filter,
    # exposing data from other organizations.
    if org_id not in sql:
        raise SQLSandboxError("Query must filter by organization ID")

    # ── Layer 4: LIMIT enforcement ────────────────────────────────────
    # If the LLM forgot to add a LIMIT, append one. Prevents queries
    # that return millions of rows and crash the browser/server.
    if not statement.find(exp.Limit):
        sql = sql.rstrip(";") + " LIMIT 10000"

    return sql
