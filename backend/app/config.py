"""
Application configuration via environment variables.

Uses pydantic-settings which automatically reads from:
1. Environment variables (highest priority)
2. The .env file at the project root (fallback)

This means you can either export OPENAI_API_KEY in your shell,
or put it in the .env file - both work.
"""

from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # Required for NL-to-SQL pipeline. Read from OPENAI_API_KEY env var.
    openai_api_key: str = ""

    # DuckDB file path. Resolved relative to project root: <project>/data/analytics.duckdb
    # Path(__file__) is config.py -> .parent is app/ -> .parent is backend/ -> .parent is project root
    duckdb_path: str = str(Path(__file__).parent.parent.parent / "data" / "analytics.duckdb")

    session_expiry_hours: int = 24
    max_batch_size: int = 1000
    max_query_rows: int = 10000

    # CORS: only the Vite dev server is allowed to make cross-origin requests
    cors_origins: list[str] = ["http://localhost:5173"]

    model_config = {
        # Points to the .env file at the project root (not inside backend/)
        "env_file": str(Path(__file__).parent.parent.parent / ".env"),
        "env_file_encoding": "utf-8",
    }


# Singleton - imported throughout the app as `from app.config import settings`
settings = Settings()
