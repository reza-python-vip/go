"""Health endpoints module moved into package.

This file contains the FastAPI `app` expected to be imported from the
`src.health` package (i.e. `from src.health import app`).
"""

from __future__ import annotations

import datetime
import logging
from pathlib import Path

from contextlib import asynccontextmanager

from fastapi import FastAPI, Response, status

from ..config import config

logger = logging.getLogger(__name__)


# This global variable is updated by the main loop to signal its current state.
main_loop_active = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """On startup, log that the service has started."""
    logger.info("Health check service started.")
    yield


app = FastAPI(
    title="Proxy Scanner Health",
    description="Provides health and readiness probes for the proxy scanner service.",
    version="2.0.0",
    lifespan=lifespan,
)


@app.get("/healthz", summary="Liveness Probe", status_code=status.HTTP_200_OK)
def liveness_probe() -> dict:
    logger.debug("Liveness probe request received.")
    return {"status": "alive"}


@app.get("/readyz", summary="Readiness Probe")
def readiness_probe(response: Response) -> dict:
    logger.debug("Readiness probe request received.")

    xray_path = Path(config.XRAY_BINARY)
    if not xray_path.is_file():
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not_ready", "reason": f"Xray binary missing at {xray_path}"}

    if main_loop_active:
        return {"status": "ready"}

    report_path = Path(config.OUTPUT_REPORT_PATH)
    if not report_path.is_file():
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "not_ready",
            "reason": f"Output report missing at {report_path}",
        }

    try:
        report_mtime = report_path.stat().st_mtime
        now = datetime.datetime.now().timestamp()
        max_age_seconds = (config.RUN_INTERVAL_MINUTES + 10) * 60

        if (now - report_mtime) > max_age_seconds:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return {
                "status": "not_ready",
                "reason": "Report file has not been updated recently.",
            }

    except OSError as e:
        logger.error(f"Could not stat report file {report_path}: {e}")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not_ready", "reason": "Could not access report file status."}

    return {"status": "ready"}
