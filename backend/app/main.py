from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.engine import DuckDBManager
from app.db.schema import initialize_schema
from app.routers import auth, ingest, organizations, query, visualizations


class AppState:
    db: DuckDBManager


app_state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app_state.db = DuckDBManager(settings.duckdb_path)
    initialize_schema(app_state.db)
    yield
    app_state.db.close()


app = FastAPI(title="Event Analytics", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(organizations.router)
app.include_router(auth.router)
app.include_router(ingest.router)
app.include_router(query.router)
app.include_router(visualizations.router)
