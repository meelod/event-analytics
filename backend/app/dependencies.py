"""
FastAPI dependency injection functions.

These are used with Depends() in route handlers to resolve the current
organization from either an API key or a session cookie. FastAPI calls
these automatically before the route handler runs. If they raise an
HTTPException, the request is rejected before hitting the handler.

This is how multi-tenant isolation is enforced at the API layer:
every route that needs org context gets it injected via these dependencies,
and all subsequent queries use that org.id to filter data.
"""

import hashlib

from fastapi import Cookie, Depends, Header, HTTPException

from app.db.engine import DuckDBManager
from app.models.organization import Organization


def get_db() -> DuckDBManager:
    """
    Returns the DuckDB connection from app state.
    Uses a lazy import to avoid circular imports (main.py imports routers,
    routers import dependencies, dependencies would import main).
    """
    from app.main import app_state
    return app_state.db


def get_current_org_from_api_key(
    x_api_key: str = Header(...),  # FastAPI extracts from X-API-Key header
    db: DuckDBManager = Depends(get_db),
) -> Organization:
    """
    API Key authentication - used for event ingestion endpoints.

    Flow:
    1. Hash the incoming key with SHA-256
    2. Look up that hash in the api_keys table
    3. Join to organizations to get the org details
    4. If no match → 401

    We never store or compare the raw key. Even if the DB is compromised,
    the attacker can't reverse SHA-256 to get usable API keys.
    The is_active check allows key revocation without deleting the row.
    """
    key_hash = hashlib.sha256(x_api_key.encode()).hexdigest()
    rows = db.execute_read(
        "SELECT o.id, o.name, o.slug FROM api_keys ak "
        "JOIN organizations o ON ak.org_id = o.id "
        "WHERE ak.key_hash = ? AND ak.is_active = true",
        (key_hash,),
    )
    if not rows:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return Organization(**rows[0])


def get_current_org_from_api_key_or_session(
    x_api_key: str | None = Header(None),
    session: str | None = Cookie(None),
    db: DuckDBManager = Depends(get_db),
) -> Organization:
    """
    Dual authentication - accepts either API key or session cookie.

    Used by POST /events so the same endpoint works for both SDK ingestion
    (API key) and the dashboard UI (session cookie). Tries API key first,
    falls back to session. Raises 401 if neither is valid.
    """
    if x_api_key:
        key_hash = hashlib.sha256(x_api_key.encode()).hexdigest()
        rows = db.execute_read(
            "SELECT o.id, o.name, o.slug FROM api_keys ak "
            "JOIN organizations o ON ak.org_id = o.id "
            "WHERE ak.key_hash = ? AND ak.is_active = true",
            (key_hash,),
        )
        if rows:
            return Organization(**rows[0])

    if session:
        rows = db.execute_read(
            "SELECT o.id, o.name, o.slug FROM sessions s "
            "JOIN organizations o ON s.org_id = o.id "
            "WHERE s.token = ? AND s.expires_at > current_timestamp",
            (session,),
        )
        if rows:
            return Organization(**rows[0])

    raise HTTPException(status_code=401, detail="Invalid API key or session")


def get_current_org_from_session(
    session: str | None = Cookie(None),  # FastAPI extracts from "session" cookie
    db: DuckDBManager = Depends(get_db),
) -> Organization:
    """
    Session authentication - used for dashboard endpoints (query, visualizations).

    Flow:
    1. Read the "session" cookie from the request
    2. Look up that token in the sessions table
    3. Check it hasn't expired (expires_at > current_timestamp)
    4. Join to organizations to get the org details
    5. If no cookie, no match, or expired → 401

    The session token is a random 32-byte URL-safe string (secrets.token_urlsafe).
    It's stored in an HttpOnly cookie, which means JavaScript can't read it -
    this prevents XSS attacks from stealing the session.
    """
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    rows = db.execute_read(
        "SELECT o.id, o.name, o.slug FROM sessions s "
        "JOIN organizations o ON s.org_id = o.id "
        "WHERE s.token = ? AND s.expires_at > current_timestamp",
        (session,),
    )
    if not rows:
        raise HTTPException(status_code=401, detail="Session expired")
    return Organization(**rows[0])
