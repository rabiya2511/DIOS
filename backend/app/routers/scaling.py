"""
Scaling & Availability router — autoscaling config/status, failover,
health/readiness/liveness probes.
Matches the Scaling & Availability section of the Deployment &
Infrastructure APIs blueprint (6/6).

ASSUMPTIONS:
- Autoscaling config is a single GLOBAL, platform-wide policy (not
  per-service or per-deployment) — POST /autoscaling replaces it wholesale.
  current_instances is a STUB: it's just reset to min_instances every time
  the policy is (re)configured. There's no real scaling loop or metrics
  feedback actually adjusting it — wire in real infrastructure metrics
  before trusting this number.
- POST /failover is a STUB: it records that a failover was "triggered" and
  returns success immediately — there's no real traffic cutover, DNS
  update, or region health check behind it.
- GET /health, /readiness, /liveness are intentionally UNAUTHENTICATED
  (no get_current_user dependency) — this matches real-world convention,
  since load balancers, Kubernetes probes, and uptime monitors calling
  these endpoints typically don't carry a user auth token. All three are
  also stubs: they always report healthy/ready/alive as long as the
  process is running, since there's no real subsystem (DB connection
  pool, downstream dependency, etc.) being checked here.

No route-ordering concerns: every path here (/autoscaling,
/autoscaling/status, /failover, /health, /readiness, /liveness) is a
flat, distinct, top-level name with no /{id} catch-alls.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends

from app.schemas.scaling import (
    AutoscalingConfigRequest,
    AutoscalingStatusResponse,
    FailoverRequest,
    FailoverResponse,
    HealthResponse,
    ReadinessResponse,
    LivenessResponse,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1", tags=["Scaling & Availability"])

# Global, platform-wide state (see docstring).
_autoscaling_config: dict = {
    "enabled": False,
    "min_instances": 1,
    "max_instances": 1,
    "target_cpu_percent": 70,
    "current_instances": 1,
    "updated_at": datetime.now(timezone.utc),
}

_CURRENT_REGION = "us-east-1"
_BACKUP_REGION = "us-west-2"


@router.post("/autoscaling", response_model=AutoscalingStatusResponse, status_code=201)
def configure_autoscaling(
    data: AutoscalingConfigRequest,
    current_user: dict = Depends(get_current_user),
):
    global _autoscaling_config
    _autoscaling_config = {
        "enabled": data.enabled,
        "min_instances": data.min_instances,
        "max_instances": data.max_instances,
        "target_cpu_percent": data.target_cpu_percent,
        # STUB: real version would come from actual scaling metrics, not a reset.
        "current_instances": data.min_instances,
        "updated_at": datetime.now(timezone.utc),
    }
    return _autoscaling_config


@router.get("/autoscaling/status", response_model=AutoscalingStatusResponse)
def get_autoscaling_status():
    return _autoscaling_config


@router.post("/failover", response_model=FailoverResponse, status_code=201)
def trigger_failover(
    data: FailoverRequest,
    current_user: dict = Depends(get_current_user),
):
    target = data.target_region or _BACKUP_REGION
    return FailoverResponse(
        id=str(uuid4()),
        from_region=_CURRENT_REGION,
        to_region=target,
        status="completed",
        triggered_by=current_user["email"],
        triggered_at=datetime.now(timezone.utc),
    )


@router.get("/health", response_model=HealthResponse)
def health_check():
    return HealthResponse(status="ok", checked_at=datetime.now(timezone.utc))


@router.get("/readiness", response_model=ReadinessResponse)
def readiness_check():
    return ReadinessResponse(ready=True, checked_at=datetime.now(timezone.utc))


@router.get("/liveness", response_model=LivenessResponse)
def liveness_check():
    return LivenessResponse(alive=True, checked_at=datetime.now(timezone.utc))