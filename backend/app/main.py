"""
FastAPI application entry point.

The lifespan context manager handles startup/shutdown:
- On startup: opens DuckDB connection, creates tables if they don't exist
- On shutdown: cleanly closes the DuckDB connection

This replaces the older @app.on_event("startup") pattern that FastAPI deprecated.

The AppState class holds the DuckDB connection as a module-level singleton.
Route handlers access it via the get_db() dependency in dependencies.py.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.engine import DuckDBManager
from app.db.schema import initialize_schema
from app.routers import auth, ingest, organizations, query, visualizations


class AppState:
    """Module-level state container. Holds the DuckDB connection."""
    db: DuckDBManager


app_state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs once on startup (before yield) and once on shutdown (after yield).
    The DuckDB connection lives for the entire server lifetime.
    """
    app_state.db = DuckDBManager(settings.duckdb_path)
    initialize_schema(app_state.db)
    yield
    app_state.db.close()


app = FastAPI(title="Event Analytics", version="0.1.0", lifespan=lifespan)

# CORS middleware: allows the React frontend (localhost:5173) to call the API (localhost:8000).
# allow_credentials=True is required because we use HttpOnly cookies for session auth -
# the browser needs permission to send cookies cross-origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all route modules. Each router handles a domain:
app.include_router(organizations.router)   # POST /api/v1/orgs
app.include_router(auth.router)            # POST /api/v1/auth/login, GET /me, POST /logout
app.include_router(ingest.router)          # POST /api/v1/events, /events/batch
app.include_router(query.router)           # POST /api/v1/query
app.include_router(visualizations.router)  # CRUD /api/v1/visualizations
