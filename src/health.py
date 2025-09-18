"""Health endpoints for service liveness/readiness probes."""

from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(title="Proxy Scanner Health")


@app.get("/healthz")
def health() -> dict:
    """Liveness probe endpoint used by containers and healthchecks."""
    return {"status": "ok"}


@app.get("/ready")
def ready() -> dict:
    """Readiness probe for load balancers. Extend this to check dependencies later."""
    # TODO: add dependency checks (DB, Storage, Cores) here
    return {"status": "ready"}
