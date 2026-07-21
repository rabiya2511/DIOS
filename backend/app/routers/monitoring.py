"""
Health & Status router — health, status, readiness, liveness.
Matches the Health & Status section of the Monitoring APIs blueprint (4/4).
STUBBED: readiness/liveness always report healthy.
"""

import time
from datetime import datetime, timezone

from fastapi import APIRouter

from app.schemas.monitoring import (
    HealthResponse,
    StatusResponse,
    ReadinessResponse,
    LivenessResponse,
)

router = APIRouter(prefix="/api/v1/monitoring", tags=["Monitoring"])

_start_time = time.monotonic()
_version = "0.1.0"


@router.get("/health", response_model=HealthResponse)
def get_health():
    return HealthResponse(status="ok", timestamp=datetime.now(timezone.utc))


@router.get("/status", response_model=StatusResponse)
def get_status():
    return StatusResponse(
        status="operational",
        uptime_seconds=round(time.monotonic() - _start_time, 2),
        version=_version,
    )


@router.get("/readiness", response_model=ReadinessResponse)
def get_readiness():
    # STUB: real version would check DB, cache, downstream dependencies, etc.
    checks = {"database": True, "cache": True}
    return ReadinessResponse(ready=all(checks.values()), checks=checks)


@router.get("/liveness", response_model=LivenessResponse)
def get_liveness():
    # STUB: real version would detect deadlocks/hangs.
    return LivenessResponse(alive=True)