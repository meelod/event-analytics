"""
Natural Language to SQL pipeline - the core intelligence of the system.

This module orchestrates the full query flow:
1. Fetch real event names/property keys from the database (dynamic context)
2. Send question + schema + context to OpenAI GPT-4o → get SQL back
3. Validate the SQL through the sandbox (sql_sandbox.py)
4. Execute the safe SQL against DuckDB
5. Send results to GPT-4o-mini → get chart configuration back
6. Return everything to the frontend

Two LLM calls per query:
- GPT-4o for SQL generation (accuracy matters - wrong SQL = wrong data)
- GPT-4o-mini for chart config (simpler task - just pick chart type + axes)

Trade-off: Two API calls add ~2-3 seconds latency total. A single call could
do both, but splitting them gives better reliability. If the chart config
call fails, we still have valid data. If SQL generation fails, we don't
waste money on a chart config call.

The system prompt is carefully engineered:
- Gives the exact schema with column types
- Hardcodes org_id filter requirement (multi-tenant isolation)
- Specifies DuckDB-specific syntax (date_trunc, json_extract_string)
- Provides patterns for common queries (DAU, conversion, top events)
- Explicitly forbids dangerous operations
"""

import time

import openai

from app.config import settings
from app.db.engine import DuckDBManager
from app.services.chart_config import generate_chart_config
from app.services.sql_sandbox import SQLSandboxError, validate_sql

# The system prompt tells the LLM what it is, what schema it's working with,
# and what rules to follow. {org_id} is replaced at runtime with the actual
# organization ID so the LLM hardcodes it into the WHERE clause.
SYSTEM_PROMPT = """You are a SQL query generator for an event analytics platform.
You translate natural language questions into DuckDB SQL queries.

DATABASE SCHEMA:
- Table: events
  Columns:
    - id: VARCHAR (event UUID)
    - org_id: VARCHAR (organization ID) -- ALWAYS filter by this
    - event_name: VARCHAR (e.g., "page_view", "signup", "purchase")
    - distinct_id: VARCHAR (unique user/entity identifier)
    - timestamp: TIMESTAMP (when the event occurred)
    - properties: JSON (arbitrary key-value pairs, access via json_extract_string(properties, '$.key_name'))
    - ingested_at: TIMESTAMP

RULES:
1. ALWAYS include WHERE org_id = '{org_id}' in every query.
2. Only generate SELECT statements. Never INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, or any DDL/DML.
3. Use DuckDB SQL syntax. For JSON property access use: json_extract_string(properties, '$.key_name').
4. For time-based queries, use DuckDB date functions: date_trunc, date_part, current_timestamp, interval.
5. Limit results to 10000 rows maximum using LIMIT.
6. Return ONLY the SQL query, no explanations, no markdown code fences.
7. For "daily active users" use COUNT(DISTINCT distinct_id) grouped by date_trunc('day', timestamp).
8. For "events over time" use COUNT(*) grouped by date_trunc appropriate to the time range.
9. Always alias computed columns with readable names (e.g., AS daily_users, AS event_count).
10. Never use file-reading functions, COPY, EXPORT, or any I/O operations.
11. Always ORDER BY the time/date column when grouping by time.
12. For "conversion" queries, use conditional counting: COUNT(DISTINCT CASE WHEN event_name = 'X' THEN distinct_id END).
13. Cast date_trunc results to DATE for cleaner output: CAST(date_trunc('day', timestamp) AS DATE).
"""


def get_org_context(org_id: str, db: DuckDBManager) -> str:
    """
    Query the actual database to find what event names and property keys
    exist for this org. This is appended to the system prompt so the LLM
    uses real event names instead of guessing.

    Without this, the LLM might generate WHERE event_name = 'page_click'
    when the actual event is called 'button_click'. This was a real bug
    we hit - the fix is to give the LLM ground truth from the database.
    """
    # Get event names with counts so the LLM knows the data distribution
    event_names = db.execute_read(
        "SELECT event_name, COUNT(*) as count FROM events "
        "WHERE org_id = ? GROUP BY event_name ORDER BY count DESC",
        (org_id,),
    )
    # Get all unique JSON property keys across all events
    props = db.execute_read(
        "SELECT DISTINCT json_keys(properties::JSON) as keys FROM events "
        "WHERE org_id = ? LIMIT 100",
        (org_id,),
    )
    # Flatten the list of key-lists into a single set
    prop_keys = set()
    for row in props:
        if row["keys"]:
            for k in row["keys"]:
                prop_keys.add(k)

    # Build a human-readable context block for the LLM
    lines = ["AVAILABLE EVENT NAMES (use these exactly, do not invent names):"]
    for row in event_names:
        lines.append(f"  - \"{row['event_name']}\" ({row['count']} events)")
    if prop_keys:
        lines.append(f"\nKNOWN PROPERTY KEYS: {', '.join(sorted(prop_keys))}")
    return "\n".join(lines)


async def generate_sql(question: str, org_id: str, db: DuckDBManager) -> str:
    """
    Call OpenAI GPT-4o to translate a natural language question into SQL.

    temperature=0 makes the output deterministic - same question always
    produces the same SQL. This is important for reproducibility.

    max_tokens=500 is enough for any reasonable analytics query.
    """
    context = get_org_context(org_id, db)
    client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.chat.completions.create(
        model="gpt-4o",
        temperature=0,
        max_tokens=500,
        messages=[
            # System prompt = schema + rules + dynamic context (real event names)
            {"role": "system", "content": SYSTEM_PROMPT.format(org_id=org_id) + "\n" + context},
            {"role": "user", "content": f"Question: {question}"},
        ],
    )
    sql = response.choices[0].message.content.strip()
    # Some models wrap SQL in markdown code fences despite being told not to.
    # Strip them if present.
    if sql.startswith("```"):
        sql = sql.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return sql


async def generate_and_execute_query(
    question: str, org_id: str, db: DuckDBManager
) -> dict:
    """
    Full pipeline orchestration:
    1. LLM generates SQL from the question
    2. Sandbox validates the SQL (4 layers of checks)
    3. DuckDB executes the validated SQL
    4. Second LLM call determines chart type from the results
    5. Returns everything packaged for the frontend
    """
    # Step 1: NL → SQL via GPT-4o
    raw_sql = await generate_sql(question, org_id, db)

    # Step 2: Validate (raises SQLSandboxError if unsafe)
    safe_sql = validate_sql(raw_sql, org_id)

    # Step 3: Execute against DuckDB (read-only cursor)
    start = time.monotonic()
    rows = db.execute_read(safe_sql)
    elapsed_ms = (time.monotonic() - start) * 1000

    # Step 4: Determine chart type via GPT-4o-mini
    columns = list(rows[0].keys()) if rows else []
    chart_config = await generate_chart_config(question, safe_sql, columns, rows)

    # Step 5: Package everything for the frontend
    return {
        "question": question,
        "generated_sql": safe_sql,
        "data": rows,                              # The actual query results
        "chart_config": chart_config,               # How to render the chart
        "row_count": len(rows),
        "execution_time_ms": round(elapsed_ms, 2),  # DuckDB query time (not LLM time)
    }
