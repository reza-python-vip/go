"""Health endpoints for service liveness and readiness probes.

This module provides a small FastAPI application that can be run to expose
health check endpoints, typically used in containerized environments like
Docker or Kubernetes.
"""

from __future__ import annotations

import datetime
import logging
from pathlib import Path

from fastapi import FastAPI, Response, status

from .config import Config

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Proxy Scanner Health",
    description="Provides health and readiness probes for the proxy scanner service.",
    version="2.0.0",
)

# This global variable is updated by the main loop to signal its current state.
main_loop_active = False


@app.on_event("startup")
async def startup_event():
    """Log that the health service is starting."""
    logger.info("Health check service started.")


@app.get("/healthz", summary="Liveness Probe", status_code=status.HTTP_200_OK)
def liveness_probe() -> dict:
    """
    Liveness probe to indicate the service process is running.
    Always returns 200 OK if the web server is responsive.
    """
    logger.debug("Liveness probe request received.")
    return {"status": "alive"}


@app.get("/readyz", summary="Readiness Probe")
def readiness_probe(response: Response) -> dict:
    """
    Readiness probe to check if the service is ready to serve.

    Checks for:
    1. Existence of the Xray binary.
    2. The main loop being active OR a recent output report.
    """
    logger.debug("Readiness probe request received.")
    config = Config()

    # 1. Check for Xray binary
    xray_path = Path(config.XRAY_BINARY)
    if not xray_path.is_file():
        logger.warning(f"Readiness check failed: Xray binary not found at {xray_path}")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not_ready", "reason": f"Xray binary missing at {xray_path}"}

    # 2. Check if the loop is active or if a recent report exists
    if main_loop_active:
        logger.info("Readiness check passed (main loop active).")
        return {"status": "ready"}

    # If loop not active, check the report file as a fallback
    report_path = Path(config.OUTPUT_REPORT_PATH)
    if not report_path.is_file():
        logger.warning(
            f"Readiness check failed: Report file not found at {report_path}"
        )
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "not_ready",
            "reason": f"Output report missing at {report_path}",
        }

    try:
        report_mtime = report_path.stat().st_mtime
        now = datetime.datetime.now().timestamp()
        max_age_seconds = (
            config.RUN_INTERVAL_MINUTES + 10
        ) * 60  # Interval + 10min grace

        if (now - report_mtime) > max_age_seconds:
            logger.warning("Readiness check failed: Report file is too old.")
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return {
                "status": "not_ready",
                "reason": "Report file has not been updated recently.",
            }

    except OSError as e:
        logger.error(f"Could not stat report file {report_path}: {e}")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not_ready", "reason": "Could not access report file status."}

    logger.info("Readiness check passed (recent report found).")
    return {"status": "ready"}
