"""
Event ingestion API routes.

Two endpoints:
- POST /events     → single event (returns event_id)
- POST /events/batch → up to 1000 events (returns accepted count + errors)

Both use API key auth (X-API-Key header). The org_id is resolved from the
key via the get_current_org_from_api_key dependency - clients never specify
their own org_id, preventing cross-tenant data injection.

The single event endpoint wraps the event in a list and reuses the batch
ingestion service. This avoids duplicating logic.
"""

from fastapi import APIRouter, Depends

from app.db.engine import DuckDBManager
from app.dependencies import get_current_org_from_api_key, get_db
from app.models.event import BatchResponse, EventBatchIn, EventIn, EventResponse
from app.models.organization import Organization
from app.services.ingestion import ingest_events

router = APIRouter(prefix="/api/v1", tags=["ingestion"])


@router.post("/events", response_model=EventResponse, status_code=201)
async def ingest_single_event(
    event: EventIn,
    org: Organization = Depends(get_current_org_from_api_key),
    db: DuckDBManager = Depends(get_db),
):
    """Ingest one event. Auth: X-API-Key header."""
    accepted, errors, event_ids = await ingest_events(db, org.id, [event])
    return EventResponse(event_id=event_ids[0])


@router.post("/events/batch", response_model=BatchResponse, status_code=201)
async def ingest_batch_events(
    batch: EventBatchIn,
    org: Organization = Depends(get_current_org_from_api_key),
    db: DuckDBManager = Depends(get_db),
):
    """Ingest up to 1000 events. Auth: X-API-Key header."""
    accepted, errors, event_ids = await ingest_events(db, org.id, batch.events)
    return BatchResponse(accepted=accepted, errors=errors)
