"""
Event ingestion service.

Handles the pipeline from raw API input to database storage:
1. Validate each event (Pydantic already did structural validation)
2. Normalize: set defaults (timestamp, UUID), serialize properties to JSON
3. Batch insert via DuckDB's executemany for performance

executemany sends all rows in a single operation, which is significantly
faster than individual INSERT statements. DuckDB optimizes this internally
by batching the columnar writes.

Trade-off: We don't do any deduplication. If the same event is sent twice,
it's stored twice. Mixpanel handles this with a $insert_id field. For a
take-home, append-only is the right simplicity trade-off.
"""

import json
import uuid
from datetime import datetime, timezone

from app.db.engine import DuckDBManager
from app.models.event import EventIn


def prepare_row(org_id: str, event: EventIn) -> tuple:
    """
    Transform a validated Pydantic EventIn into a tuple for INSERT.

    Key decisions:
    - Generate UUID server-side (not client-side) for consistency
    - Default timestamp to now if the client didn't provide one
    - Serialize properties dict to a JSON string for DuckDB's JSON column
    - ingested_at is always server time (when we received it, not when it happened)
    """
    event_id = str(uuid.uuid4())
    ts = event.timestamp or datetime.now(timezone.utc)
    props_json = json.dumps(event.properties) if event.properties else "{}"
    now = datetime.now(timezone.utc)
    # Tuple order must match the INSERT column order exactly
    return (event_id, org_id, event.event, event.distinct_id, ts, props_json, now)


async def ingest_events(
    db: DuckDBManager, org_id: str, events: list[EventIn]
) -> tuple[int, list[dict], list[str]]:
    """
    Ingest a list of events. Returns (accepted_count, errors, event_ids).

    The org_id comes from the authenticated API key (see dependencies.py),
    NOT from the request body. This is critical for multi-tenant isolation -
    a client can't send events to a different org by spoofing the org_id field.

    Errors are collected per-event so a single bad event in a batch of 1000
    doesn't reject the entire batch. This is the "partial success" pattern
    common in ingestion APIs.
    """
    rows = []
    errors = []
    event_ids = []
    for i, event in enumerate(events):
        try:
            row = prepare_row(org_id, event)
            rows.append(row)
            event_ids.append(row[0])  # row[0] is the generated event_id
        except (ValueError, TypeError) as e:
            errors.append({"index": i, "error": str(e)})

    if rows:
        # executemany batches all inserts into a single DuckDB operation.
        # The write lock in DuckDBManager ensures this doesn't conflict
        # with other concurrent writes.
        await db.execute_write(
            "INSERT INTO events (id, org_id, event_name, distinct_id, timestamp, properties, ingested_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows,
        )

    return len(rows), errors, event_ids
