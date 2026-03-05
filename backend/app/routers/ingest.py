"""
Event ingestion API routes.

Two ingestion endpoints:
- POST /events       → single event (API key OR session cookie)
- POST /events/batch → up to 1000 events (API key only)

POST /events accepts dual auth so it works from both SDK/curl (API key)
and the dashboard UI (session cookie). POST /events/batch is API-key-only
since batch ingestion is an SDK concern, not a UI one.

Both resolve org_id from auth (never from the request body) to prevent
cross-tenant data injection.
"""

from fastapi import APIRouter, Depends

from app.db.engine import DuckDBManager
from app.dependencies import get_current_org_from_api_key, get_current_org_from_api_key_or_session, get_current_org_from_session, get_db
from app.models.event import BatchResponse, EventBatchIn, EventIn, EventResponse, SeedRequest, SeedResponse
from app.models.organization import Organization
from app.services.ingestion import ingest_events
from app.services.seeding import seed_demo_events

router = APIRouter(prefix="/api/v1", tags=["ingestion"])


@router.post("/events", response_model=EventResponse, status_code=201)
async def ingest_single_event(
    event: EventIn,
    org: Organization = Depends(get_current_org_from_api_key_or_session),
    db: DuckDBManager = Depends(get_db),
):
    """Ingest one event. Auth: API key header OR session cookie."""
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


@router.post("/events/seed", response_model=SeedResponse, status_code=201)
async def seed_events(
    body: SeedRequest,
    org: Organization = Depends(get_current_org_from_session),
    db: DuckDBManager = Depends(get_db),
):
    """
    Seed randomized demo events for the current org.

    Auth: Session cookie (dashboard feature, not SDK).
    Generates realistic events with weighted distributions across
    7 event types (page_view, signup, login, button_click, purchase,
    feature_used, error) spread over the requested time range.
    """
    result = await seed_demo_events(db, org.id, count=body.count, days_back=body.days_back)
    return SeedResponse(inserted=result["inserted"], distribution=result["distribution"])
