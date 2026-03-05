"""
Chart Configuration Generator.

After the SQL query executes and we have tabular results, this module
calls GPT-4o-mini to determine the best chart type and configuration.

Uses GPT-4o-mini (not GPT-4o) because this is a simpler classification task:
given column names and sample data, pick one of 5 chart types and map
columns to axes. The cheaper model is accurate enough and saves ~50% cost.

The output is a JSON object that maps directly to Recharts component props
on the frontend. The frontend's ChartRenderer.tsx reads this config and
renders the appropriate chart without any additional logic.

Trade-off: Could be done deterministically with heuristics (e.g., "if one
column is a date, use a line chart"). But the LLM handles edge cases better
(multi-series, ambiguous data shapes) and the cost is ~$0.001 per call.
"""

import json

import openai

from app.config import settings

# This prompt constrains the LLM to return a specific JSON shape that
# the frontend can consume directly. The guidelines encode visualization
# best practices (time series → line, categories → bar, etc.)
CHART_SYSTEM_PROMPT = """You are a data visualization assistant. Given a SQL query and its result columns,
determine the best chart type and configuration.

Return a JSON object with:
{
  "chart_type": "line" | "bar" | "area" | "pie" | "number",
  "title": "descriptive title",
  "x_axis": "column_name for x-axis" or null,
  "y_axis": "column_name for y-axis" or null,
  "series": [{"dataKey": "column_name", "name": "Display Name", "color": "#hex"}]
}

Guidelines:
- Time series data -> "line" or "area"
- Categorical comparisons -> "bar"
- Proportions -> "pie" (only when <= 10 categories)
- Single aggregate value -> "number"
- Always use readable display names
- Use distinct colors for each series: #8884d8, #82ca9d, #ffc658, #ff7300, #0088fe
Return ONLY valid JSON, no markdown fences, no explanation."""


async def generate_chart_config(
    question: str, sql: str, columns: list[str], sample_rows: list[dict]
) -> dict:
    """
    Call GPT-4o-mini with the query context and get back a chart config JSON.

    We send:
    - The original question (helps the LLM understand intent)
    - The SQL (shows the structure of the data)
    - Column names (what axes are available)
    - First 3 rows of data (helps identify data types and ranges)

    Only 3 rows are sent to minimize token usage. The LLM doesn't need
    all 10,000 rows to decide "this is a time series, use a line chart."
    """
    client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
    user_msg = (
        f"Question: {question}\n"
        f"SQL: {sql}\n"
        f"Columns: {columns}\n"
        # default=str handles datetime objects that aren't JSON-serializable
        f"Sample data (first 3 rows): {json.dumps(sample_rows[:3], default=str)}"
    )
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,  # Deterministic - same data shape → same chart type
        max_tokens=300,
        messages=[
            {"role": "system", "content": CHART_SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
    )
    config_str = response.choices[0].message.content.strip()
    # Strip markdown fences if the model wraps the JSON
    if config_str.startswith("```"):
        config_str = config_str.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return json.loads(config_str)
