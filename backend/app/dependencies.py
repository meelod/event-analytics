import hashlib

from fastapi import Cookie, Depends, Header, HTTPException

from app.db.engine import DuckDBManager
from app.models.organization import Organization


def get_db() -> DuckDBManager:
    from app.main import app_state
    return app_state.db


def get_current_org_from_api_key(
    x_api_key: str = Header(...),
    db: DuckDBManager = Depends(get_db),
) -> Organization:
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


def get_current_org_from_session(
    session: str | None = Cookie(None),
    db: DuckDBManager = Depends(get_db),
) -> Organization:
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
