from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from db import migrate
from routers import audit, auth, billing, comparison, office, overview, prospects, settings as settings_router, tracking
from seed import seed_demo
from services.admins import ensure_admins
from services.prospects import import_legacy_file


@asynccontextmanager
async def lifespan(_app: FastAPI):
    migrate()
    if settings.seed_demo:
        seed_demo()
    ensure_admins()
    import_legacy_file()
    yield


app = FastAPI(
    title="Meridian GEO API",
    version="0.1.0",
    summary="Suivi de visibilité, audit GEO et recommandations.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(overview.router, prefix="/api/v1")
app.include_router(tracking.router, prefix="/api/v1")
app.include_router(comparison.router, prefix="/api/v1")
app.include_router(audit.router, prefix="/api/v1")
app.include_router(settings_router.router, prefix="/api/v1")
app.include_router(prospects.router, prefix="/api/v1")
app.include_router(billing.router, prefix="/api/v1")
app.include_router(office.router, prefix="/api/v1")


@app.get("/api/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
