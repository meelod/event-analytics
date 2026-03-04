import json
import uuid
from datetime import datetime, timezone

from app.db.engine import DuckDBManager
from app.models.event import EventIn


def prepare_row(org_id: str, event: EventIn) -> tuple:
    event_id = str(uuid.uuid4())
    ts = event.timestamp or datetime.now(timezone.utc)
    props_json = json.dumps(event.properties) if event.properties else "{}"
    now = datetime.now(timezone.utc)
    return (event_id, org_id, event.event, event.distinct_id, ts, props_json, now)


async def ingest_events(
    db: DuckDBManager, org_id: str, events: list[EventIn]
) -> tuple[int, list[dict], list[str]]:
    """Returns (accepted_count, errors, event_ids)."""
    rows = []
    errors = []
    event_ids = []
    for i, event in enumerate(events):
        try:
            row = prepare_row(org_id, event)
            rows.append(row)
            event_ids.append(row[0])
        except (ValueError, TypeError) as e:
            errors.append({"index": i, "error": str(e)})

    if rows:
        await db.execute_write(
            "INSERT INTO events (id, org_id, event_name, distinct_id, timestamp, properties, ingested_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows,
        )

    return len(rows), errors, event_ids
