import time

import openai

from app.config import settings
from app.db.engine import DuckDBManager
from app.services.chart_config import generate_chart_config
from app.services.sql_sandbox import SQLSandboxError, validate_sql

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
    """Fetch actual event names and property keys to give the LLM real context."""
    event_names = db.execute_read(
        "SELECT event_name, COUNT(*) as count FROM events "
        "WHERE org_id = ? GROUP BY event_name ORDER BY count DESC",
        (org_id,),
    )
    props = db.execute_read(
        "SELECT DISTINCT json_keys(properties::JSON) as keys FROM events "
        "WHERE org_id = ? LIMIT 100",
        (org_id,),
    )
    # Flatten and dedupe property keys
    prop_keys = set()
    for row in props:
        if row["keys"]:
            for k in row["keys"]:
                prop_keys.add(k)

    lines = ["AVAILABLE EVENT NAMES (use these exactly, do not invent names):"]
    for row in event_names:
        lines.append(f"  - \"{row['event_name']}\" ({row['count']} events)")
    if prop_keys:
        lines.append(f"\nKNOWN PROPERTY KEYS: {', '.join(sorted(prop_keys))}")
    return "\n".join(lines)


async def generate_sql(question: str, org_id: str, db: DuckDBManager) -> str:
    context = get_org_context(org_id, db)
    client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.chat.completions.create(
        model="gpt-4o",
        temperature=0,
        max_tokens=500,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT.format(org_id=org_id) + "\n" + context},
            {"role": "user", "content": f"Question: {question}"},
        ],
    )
    sql = response.choices[0].message.content.strip()
    if sql.startswith("```"):
        sql = sql.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return sql


async def generate_and_execute_query(
    question: str, org_id: str, db: DuckDBManager
) -> dict:
    raw_sql = await generate_sql(question, org_id, db)
    safe_sql = validate_sql(raw_sql, org_id)

    start = time.monotonic()
    rows = db.execute_read(safe_sql)
    elapsed_ms = (time.monotonic() - start) * 1000

    columns = list(rows[0].keys()) if rows else []
    chart_config = await generate_chart_config(question, safe_sql, columns, rows)

    return {
        "question": question,
        "generated_sql": safe_sql,
        "data": rows,
        "chart_config": chart_config,
        "row_count": len(rows),
        "execution_time_ms": round(elapsed_ms, 2),
    }
