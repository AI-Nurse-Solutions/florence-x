"""Florence-X API entrypoint. Run: uvicorn app.main:app --reload (from apps/api)."""
from __future__ import annotations

from fastapi import FastAPI

from .config import settings
from .middleware import ZeroTrustMiddleware
from .routes import edena, events, registry, reviews, runs, signals
from .telemetry import setup_telemetry

# Configure OpenTelemetry export when an OTLP endpoint is set (no-op otherwise).
setup_telemetry()

app = FastAPI(
    title="Florence-X API",
    version="0.1.0",
    description="Governance-first AI orchestration control plane. EDENA gates every action.",
)
app.add_middleware(ZeroTrustMiddleware, require_identity=settings.require_identity)

app.include_router(signals.router)
app.include_router(runs.router)
app.include_router(reviews.router)
app.include_router(registry.router)
app.include_router(events.router)
app.include_router(edena.router)  # reference EDENA (see routes/edena.py docstring)


@app.get("/healthz", tags=["meta"])
def healthz() -> dict:
    return {"status": "ok", "service": "florence-x", "version": "0.1.0"}
