"""Health endpoints for service liveness and readiness probes.

This module provides a small FastAPI application that can be run to expose
health check endpoints, typically used in containerized environments like Docker or Kubernetes.
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, Response, status

from .config import Config

# Configure logging for the health service
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Proxy Scanner Health",
    description="Provides health and readiness probes for the proxy scanner service.",
    version="1.0.0"
)


@app.on_event("startup")
async def startup_event():
    """Log that the health service is starting."""
    logger.info("Health check service started.")


@app.get("/healthz", summary="Liveness Probe")
def liveness_probe(response: Response) -> dict:
    """Liveness probe endpoint used by containers and health checks.
    
    This endpoint should always return a 200 OK to indicate that the service process is running.
    """
    logger.debug("Liveness probe request received.")
    response.status_code = status.HTTP_200_OK
    return {"status": "alive"}


@app.get("/readyz", summary="Readiness Probe")
def readiness_probe(response: Response) -> dict:
    """Readiness probe to indicate if the service is ready to accept traffic.

    This checks for the existence of the core binaries (Xray and Hiddify).
    If they are missing, it returns a 503 Service Unavailable status.
    """
    logger.debug("Readiness probe request received.")
    
    xray_path = Path(Config.XRAY_BINARY)
    hiddify_path = Path(Config.HIDDIFY_BINARY)

    missing_files = []
    if not xray_path.is_file():
        missing_files.append(f"Xray binary missing at {xray_path}")
        logger.warning(f"Readiness check failed: Xray binary not found at {xray_path}")

    # Hiddify is optional, but we can log its absence
    if not hiddify_path.is_file():
        logger.warning(f"Hiddify binary not found at {hiddify_path}. This may be acceptable.")

    if missing_files:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not_ready", "dependencies": missing_files}

    logger.info("Readiness check passed. Core binaries are present.")
    response.status_code = status.HTTP_200_OK
    return {"status": "ready"}


# To run this app for testing: uvicorn src.health:app --reload
