from app.db.engine import DuckDBManager

TABLES = [
    """
    CREATE TABLE IF NOT EXISTS organizations (
        id          VARCHAR PRIMARY KEY,
        name        VARCHAR NOT NULL,
        slug        VARCHAR NOT NULL UNIQUE,
        created_at  TIMESTAMP NOT NULL DEFAULT current_timestamp,
        updated_at  TIMESTAMP NOT NULL DEFAULT current_timestamp
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS api_keys (
        id          VARCHAR PRIMARY KEY,
        org_id      VARCHAR NOT NULL,
        key_prefix  VARCHAR NOT NULL,
        key_hash    VARCHAR NOT NULL,
        label       VARCHAR NOT NULL DEFAULT 'default',
        is_active   BOOLEAN NOT NULL DEFAULT true,
        created_at  TIMESTAMP NOT NULL DEFAULT current_timestamp,
        last_used_at TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS events (
        id          VARCHAR,
        org_id      VARCHAR NOT NULL,
        event_name  VARCHAR NOT NULL,
        distinct_id VARCHAR NOT NULL,
        timestamp   TIMESTAMP NOT NULL,
        properties  JSON,
        ingested_at TIMESTAMP NOT NULL DEFAULT current_timestamp
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS saved_visualizations (
        id          VARCHAR PRIMARY KEY,
        org_id      VARCHAR NOT NULL,
        title       VARCHAR NOT NULL,
        nl_question VARCHAR NOT NULL,
        generated_sql VARCHAR NOT NULL,
        result_data JSON NOT NULL,
        chart_config JSON NOT NULL,
        created_at  TIMESTAMP NOT NULL DEFAULT current_timestamp,
        updated_at  TIMESTAMP NOT NULL DEFAULT current_timestamp
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sessions (
        id          VARCHAR PRIMARY KEY,
        org_id      VARCHAR NOT NULL,
        token       VARCHAR NOT NULL UNIQUE,
        created_at  TIMESTAMP NOT NULL DEFAULT current_timestamp,
        expires_at  TIMESTAMP NOT NULL
    )
    """,
]


def initialize_schema(db: DuckDBManager):
    for ddl in TABLES:
        db.execute_write_sync(ddl)
