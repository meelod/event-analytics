import json

import openai

from app.config import settings

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
    client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
    user_msg = (
        f"Question: {question}\n"
        f"SQL: {sql}\n"
        f"Columns: {columns}\n"
        f"Sample data (first 3 rows): {json.dumps(sample_rows[:3], default=str)}"
    )
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        max_tokens=300,
        messages=[
            {"role": "system", "content": CHART_SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
    )
    config_str = response.choices[0].message.content.strip()
    if config_str.startswith("```"):
        config_str = config_str.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return json.loads(config_str)
