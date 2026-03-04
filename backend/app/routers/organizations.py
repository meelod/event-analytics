import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.db.engine import DuckDBManager
from app.dependencies import get_db
from app.models.organization import OrgCreate, OrgResponse
from app.utils.api_key import generate_api_key, hash_api_key, key_prefix

router = APIRouter(prefix="/api/v1", tags=["organizations"])


@router.post("/orgs", response_model=OrgResponse, status_code=201)
async def create_organization(body: OrgCreate, db: DuckDBManager = Depends(get_db)):
    existing = db.execute_read(
        "SELECT id FROM organizations WHERE slug = ?", (body.slug,)
    )
    if existing:
        raise HTTPException(status_code=409, detail="Organization slug already exists")

    org_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    await db.execute_write(
        "INSERT INTO organizations (id, name, slug, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        [(org_id, body.name, body.slug, now, now)],
    )

    raw_key = generate_api_key()
    key_id = str(uuid.uuid4())
    await db.execute_write(
        "INSERT INTO api_keys (id, org_id, key_prefix, key_hash, label, is_active, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        [(key_id, org_id, key_prefix(raw_key), hash_api_key(raw_key), "default", True, now)],
    )

    return OrgResponse(
        id=org_id,
        name=body.name,
        slug=body.slug,
        api_key=raw_key,
        created_at=now,
    )
