"""
Model Monitoring router — metrics, usage, latency, errors, health, costs,
cache/clear, logs.
Matches the Monitoring section of the Model Management APIs blueprint
(8/8).

*** ROUTING NOTE — READ THIS FIRST ***
/metrics, /usage, /latency, /errors, /health, /costs, /logs are all
SINGLE-SEGMENT literal paths under /api/v1/models — the exact same shape
as model_registry.py's dynamic GET/PATCH/DELETE /{id}. This router MUST
be registered in main.py BEFORE model_registry.router, or requests like
GET /models/metrics will be swallowed by model_registry's /{id} route
(treating "metrics" as a model id) instead of reaching this router.
(/cache/clear is a 2-segment path and has no such conflict, but keep it
with the rest of this router for consistency.)

WHAT'S REAL VS. NOT HERE:
- GET /models/metrics and GET /models/health are REAL aggregations
  computed directly from models_db (model_registry.py) — actual counts
  of real registered models, not fabricated.
- GET /models/usage, /models/latency, /models/errors, /models/costs, and
  /models/logs are honestly EMPTY/ZERO right now, not fabricated with
  fake numbers — there is no Inference domain built yet in this codebase
  to generate real request/token/latency/error/cost telemetry. The
  in-memory stores below (_model_usage_db etc.) are structured so that a
  future inference.py could genuinely increment them per real request;
  until that's wired in, these endpoints correctly report "nothing has
  happened yet" rather than making up plausible-looking numbers.
- POST /models/cache/clear operates on a placeholder cache dict that
  nothing else in the codebase populates yet, same pattern as
  files_admin.py's cache endpoint.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.schemas.model_monitoring import (
    ModelMetricsResponse,
    ModelUsageResponse,
    ModelLatencyResponse,
    ModelErrorsResponse,
    ModelHealthResponse,
    ModelCostsResponse,
    CacheClearResponse,
    ModelLogsResponse,
)
from app.routers.model_registry import models_db
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/models", tags=["Model Monitoring"])

# Structured for future real telemetry — currently always empty/zero.
# See module docstring.
_model_usage_db: dict[str, dict] = {}  # model_name -> {requests, tokens, latency_ms_total, errors, cost_usd}

_model_cache: dict = {}


@router.get("/metrics", response_model=ModelMetricsResponse)
def get_model_metrics(current_user: dict = Depends(get_current_user)):
    owned = [m for m in models_db.values() if m["owner_email"] == current_user["email"]]
    active = sum(1 for m in owned if m["status"] == "active")
    archived = sum(1 for m in owned if m["status"] == "archived")
    by_provider: dict[str, int] = {}
    for m in owned:
        by_provider[m["provider"]] = by_provider.get(m["provider"], 0) + 1
    return ModelMetricsResponse(
        total_models=len(owned), active_count=active, archived_count=archived, by_provider=by_provider,
    )


@router.get("/usage", response_model=ModelUsageResponse)
def get_model_usage(current_user: dict = Depends(get_current_user)):
    # Honestly empty — no Inference domain exists yet to populate this. See docstring.
    return ModelUsageResponse(total_requests=0, total_tokens=0, by_model={})


@router.get("/latency", response_model=ModelLatencyResponse)
def get_model_latency(current_user: dict = Depends(get_current_user)):
    # Honestly empty — no real request telemetry exists yet. See docstring.
    return ModelLatencyResponse(avg_latency_ms=0.0, by_model={})


@router.get("/errors", response_model=ModelErrorsResponse)
def get_model_errors(current_user: dict = Depends(get_current_user)):
    # Honestly empty — no real request telemetry exists yet. See docstring.
    return ModelErrorsResponse(total_errors=0, by_model={})


@router.get("/health", response_model=ModelHealthResponse)
def get_model_health():
    return ModelHealthResponse(
        status="ok", total_models_tracked=len(models_db), checked_at=datetime.now(timezone.utc),
    )


@router.get("/costs", response_model=ModelCostsResponse)
def get_model_costs(current_user: dict = Depends(get_current_user)):
    # Honestly zero — no real usage/billing telemetry exists yet. See docstring.
    return ModelCostsResponse(total_cost_usd=0.0, by_model={})


@router.post("/cache/clear", response_model=CacheClearResponse)
def clear_model_cache():
    cleared_count = len(_model_cache)
    _model_cache.clear()
    return CacheClearResponse(cleared_count=cleared_count, cleared_at=datetime.now(timezone.utc))


@router.get("/logs", response_model=ModelLogsResponse)
def get_model_logs(current_user: dict = Depends(get_current_user)):
    # Honestly empty — no real request logging pipeline exists yet. See docstring.
    return ModelLogsResponse(logs=[])