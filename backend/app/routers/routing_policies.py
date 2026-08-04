"""
Routing & Policies router — model routing rules, fallback, weights,
tenant policies, config, A/B tests, circuit breaker.
Matches the Routing & Policies section of the Model Management APIs
blueprint (8/8).

ASSUMPTIONS:
- This is GLOBAL, platform-wide routing configuration, not per-user —
  same pattern as networking.py / scaling.py. SAME CAVEAT: there is NO
  admin-role restriction here. Any authenticated user can currently
  rewrite routing rules, weights, tenant policies, or trip a circuit
  breaker for any model. This is almost certainly too permissive for a
  real deployment — add a role check (roles.py/permissions.py exist in
  this codebase) before relying on this for anything real.
- POST /routing/weights REPLACES the entire weights map, not a merge —
  and does NOT validate that weights sum to 1.0 (no real traffic-splitting
  engine sits behind this to enforce it; it's just recorded as given).
- POST /routing/ab-test and POST /routing/circuit-breaker are bookkeeping
  only — there is no real traffic splitter or failure-detection system
  actually routing requests based on any of this. An A/B test "runs"
  simply by existing in ab_tests_db; a circuit breaker "opening" simply
  flips a status flag. Nothing here actually intercepts or redirects real
  inference traffic.

No route-ordering concerns: /routing/model, /routing/fallback,
/routing/weights, /routing/tenant-policy, /routing/config,
/routing/ab-test, /routing/circuit-breaker are all flat, distinct
literal paths with no /{id} anywhere in this section.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends

from app.schemas.routing_policies import (
    RoutingModelRequest,
    RoutingModelResponse,
    RoutingFallbackRequest,
    RoutingFallbackResponse,
    RoutingWeightsRequest,
    RoutingWeightsResponse,
    TenantPolicyRequest,
    TenantPolicyResponse,
    RoutingConfigUpdateRequest,
    RoutingConfigResponse,
    AbTestRequest,
    AbTestResponse,
    CircuitBreakerRequest,
    CircuitBreakerResponse,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/routing", tags=["Routing & Policies"])

# Global, platform-wide state (see docstring).
_routes: dict[str, str] = {}
_fallbacks: dict[str, str] = {}
_weights: dict[str, float] = {}
_tenant_policies: dict[str, dict] = {}
_ab_tests: dict[str, dict] = {}
_circuit_breakers: dict[str, dict] = {}

_config_extras: dict = {
    "sticky_sessions": False,
    "max_retries": 2,
    "updated_at": datetime.now(timezone.utc),
}


@router.post("/model", response_model=RoutingModelResponse, status_code=201)
def set_routing_model(data: RoutingModelRequest, current_user: dict = Depends(get_current_user)):
    now = datetime.now(timezone.utc)
    _routes[data.route_key] = data.model
    return RoutingModelResponse(route_key=data.route_key, model=data.model, updated_at=now)


@router.post("/fallback", response_model=RoutingFallbackResponse, status_code=201)
def set_routing_fallback(data: RoutingFallbackRequest, current_user: dict = Depends(get_current_user)):
    now = datetime.now(timezone.utc)
    _fallbacks[data.route_key] = data.fallback_model
    return RoutingFallbackResponse(route_key=data.route_key, fallback_model=data.fallback_model, updated_at=now)


@router.post("/weights", response_model=RoutingWeightsResponse, status_code=201)
def set_routing_weights(data: RoutingWeightsRequest, current_user: dict = Depends(get_current_user)):
    global _weights
    now = datetime.now(timezone.utc)
    _weights = dict(data.weights)
    return RoutingWeightsResponse(weights=_weights, updated_at=now)


@router.post("/tenant-policy", response_model=TenantPolicyResponse, status_code=201)
def set_tenant_policy(data: TenantPolicyRequest, current_user: dict = Depends(get_current_user)):
    now = datetime.now(timezone.utc)
    _tenant_policies[data.tenant_id] = {
        "tenant_id": data.tenant_id,
        "model": data.model,
        "fallback_model": data.fallback_model,
        "weights": data.weights,
        "updated_at": now,
    }
    return _tenant_policies[data.tenant_id]


@router.get("/config", response_model=RoutingConfigResponse)
def get_routing_config():
    return RoutingConfigResponse(
        routes=_routes,
        fallbacks=_fallbacks,
        weights=_weights,
        tenant_policy_count=len(_tenant_policies),
        sticky_sessions=_config_extras["sticky_sessions"],
        max_retries=_config_extras["max_retries"],
        updated_at=_config_extras["updated_at"],
    )


@router.patch("/config", response_model=RoutingConfigResponse)
def update_routing_config(data: RoutingConfigUpdateRequest, current_user: dict = Depends(get_current_user)):
    if data.sticky_sessions is not None:
        _config_extras["sticky_sessions"] = data.sticky_sessions
    if data.max_retries is not None:
        _config_extras["max_retries"] = data.max_retries
    _config_extras["updated_at"] = datetime.now(timezone.utc)
    return get_routing_config()


@router.post("/ab-test", response_model=AbTestResponse, status_code=201)
def create_ab_test(data: AbTestRequest, current_user: dict = Depends(get_current_user)):
    test_id = str(uuid4())
    now = datetime.now(timezone.utc)
    _ab_tests[test_id] = {
        "id": test_id,
        "name": data.name,
        "model_a": data.model_a,
        "model_b": data.model_b,
        "traffic_split": data.traffic_split,
        "status": "running",
        "created_at": now,
    }
    return _ab_tests[test_id]


@router.post("/circuit-breaker", response_model=CircuitBreakerResponse, status_code=201)
def set_circuit_breaker(data: CircuitBreakerRequest, current_user: dict = Depends(get_current_user)):
    now = datetime.now(timezone.utc)
    _circuit_breakers[data.model] = {"model": data.model, "state": data.action, "updated_at": now}
    return _circuit_breakers[data.model]