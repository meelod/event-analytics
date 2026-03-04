from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    openai_api_key: str = ""
    duckdb_path: str = str(Path(__file__).parent.parent.parent / "data" / "analytics.duckdb")
    session_expiry_hours: int = 24
    max_batch_size: int = 1000
    max_query_rows: int = 10000
    cors_origins: list[str] = ["http://localhost:5173"]

    model_config = {
        "env_file": str(Path(__file__).parent.parent.parent / ".env"),
        "env_file_encoding": "utf-8",
    }


settings = Settings()
