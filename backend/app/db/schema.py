"""
Database schema definitions.

All tables use CREATE TABLE IF NOT EXISTS so this is safe to run on every startup
(idempotent). This is simpler than a migration system like Alembic, which would be
overkill for a local-only tool. DuckDB doesn't have great migration tooling anyway.

Trade-off: No foreign key enforcement. DuckDB supports FK syntax but doesn't enforce
them by default. We rely on application-level logic (always setting org_id correctly)
rather than DB-level constraints. At scale you'd want enforced FKs.
"""

from app.db.engine import DuckDBManager

TABLES = [
    # ─── Organizations ────────────────────────────────────────────────
    # Each org is a tenant. The slug is the human-readable URL-safe identifier
    # (e.g., "acme-corp"). Multi-tenancy is enforced by always filtering on org_id.
    """
    CREATE TABLE IF NOT EXISTS organizations (
        id          VARCHAR PRIMARY KEY,
        name        VARCHAR NOT NULL,
        slug        VARCHAR NOT NULL UNIQUE,
        created_at  TIMESTAMP NOT NULL DEFAULT current_timestamp,
        updated_at  TIMESTAMP NOT NULL DEFAULT current_timestamp
    )
    """,

    # ─── API Keys ─────────────────────────────────────────────────────
    # Stores HASHED API keys (SHA-256). The raw key is shown once on creation
    # and never stored. key_prefix stores "ea_live_2d380..." for display in UI.
    # is_active allows key revocation without deletion.
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

    # ─── Events (the core analytical table) ───────────────────────────
    # This is the high-volume table. Deliberately has NO primary key -
    # DuckDB stores data in columnar format, and PKs add overhead for
    # uniqueness checks on every insert. Since events are append-only
    # (we never update/delete individual events), this is the right call.
    #
    # properties is JSON - this gives us Mixpanel-style arbitrary key/value
    # pairs per event without needing a fixed schema. DuckDB can query
    # JSON efficiently with json_extract_string(properties, '$.key').
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

    # ─── Saved Visualizations ─────────────────────────────────────────
    # Persists the full pipeline output: the original question, the generated
    # SQL, the query results, and the chart configuration. This means reloading
    # a saved viz is instant (no re-querying, no LLM call).
    #
    # Trade-off: We store the result_data snapshot. If new events come in,
    # the saved viz shows stale data. An alternative is to re-run the SQL on
    # load, but that costs latency and could fail if the schema changed.
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

    # ─── Sessions ─────────────────────────────────────────────────────
    # Dashboard auth. When you login with an API key, the server creates a
    # session row with a random token and sets it as an HttpOnly cookie.
    # expires_at is checked on every request (see dependencies.py).
    #
    # Trade-off: Sessions are never cleaned up (no TTL job). For a local tool
    # this doesn't matter. In production you'd run a periodic cleanup.
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
    """Run on every server startup. IF NOT EXISTS makes this safe to re-run."""
    for ddl in TABLES:
        db.execute_write_sync(ddl)
