"""
Authentication routes for the dashboard UI.

Login flow:
1. User enters API key in the login form
2. POST /auth/login validates the key (same logic as ingestion auth)
3. Creates a session row in the DB with a random token + 24h expiry
4. Sets the token as an HttpOnly cookie
5. All subsequent dashboard requests use this cookie

Why API key for login (instead of username/password)?
- This is a local-only tool, not a SaaS with user accounts
- The API key already exists for ingestion auth
- Avoids the complexity of password hashing, reset flows, etc.
- One secret to manage, not two

Trade-off: If the API key leaks, both ingestion AND dashboard access
are compromised. In production you'd have separate credentials.
"""

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
    # Reuse the same API key validation logic from dependencies.py.
    # This hashes the key and looks it up in the DB. Raises 401 if invalid.
    org = get_current_org_from_api_key(x_api_key=body.api_key, db=db)

    # Generate a cryptographically random session token
    # token_urlsafe(32) = 32 random bytes, base64-encoded = 43 characters
    token = secrets.token_urlsafe(32)
    session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    expires = now + timedelta(hours=settings.session_expiry_hours)

    # Store the session in the DB so we can validate it on subsequent requests
    await db.execute_write(
        "INSERT INTO sessions (id, org_id, token, created_at, expires_at) VALUES (?, ?, ?, ?, ?)",
        [(session_id, org.id, token, now, expires)],
    )

    # Set the session token as an HttpOnly cookie:
    # - httponly=True: JavaScript can't read it (prevents XSS theft)
    # - samesite="lax": cookie sent on same-site requests + top-level navigations
    # - max_age: browser deletes the cookie after this many seconds
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
    """Returns the current org. Used by the frontend on page load to check if session is valid."""
    return MeResponse(org_id=org.id, org_name=org.name, org_slug=org.slug)


@router.post("/logout")
async def logout(response: Response):
    """Deletes the session cookie. Note: doesn't invalidate the session in the DB."""
    response.delete_cookie(key="session")
    return {"status": "ok"}
