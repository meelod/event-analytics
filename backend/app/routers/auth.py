import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel

from app.config import settings
from app.db.engine import DuckDBManager
from app.dependencies import get_current_org_from_api_key, get_current_org_from_session, get_db
from app.models.organization import Organization

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginRequest(BaseModel):
    api_key: str


class LoginResponse(BaseModel):
    status: str = "ok"
    org_id: str
    org_name: str


class MeResponse(BaseModel):
    org_id: str
    org_name: str
    org_slug: str


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, response: Response, db: DuckDBManager = Depends(get_db)):
    # Reuse the API key auth dependency logic
    org = get_current_org_from_api_key(x_api_key=body.api_key, db=db)

    token = secrets.token_urlsafe(32)
    session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    expires = now + timedelta(hours=settings.session_expiry_hours)

    await db.execute_write(
        "INSERT INTO sessions (id, org_id, token, created_at, expires_at) VALUES (?, ?, ?, ?, ?)",
        [(session_id, org.id, token, now, expires)],
    )

    response.set_cookie(
        key="session",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=settings.session_expiry_hours * 3600,
    )
    return LoginResponse(org_id=org.id, org_name=org.name)


@router.get("/me", response_model=MeResponse)
async def get_me(org: Organization = Depends(get_current_org_from_session)):
    return MeResponse(org_id=org.id, org_name=org.name, org_slug=org.slug)


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key="session")
    return {"status": "ok"}
