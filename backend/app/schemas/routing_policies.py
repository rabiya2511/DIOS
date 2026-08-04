"""
Pydantic schemas for the Routing & Policies domain (Model Management
APIs blueprint).
"""

from datetime import datetime
from typing import Dict, Optional, Literal

from pydantic import BaseModel

CircuitState = Literal["closed", "open"]


class RoutingModelRequest(BaseModel):
    route_key: str = "default"
    model: str


class RoutingModelResponse(BaseModel):
    route_key: str
    model: str
    updated_at: datetime


class RoutingFallbackRequest(BaseModel):
    route_key: str = "default"
    fallback_model: str


class RoutingFallbackResponse(BaseModel):
    route_key: str
    fallback_model: str
    updated_at: datetime


class RoutingWeightsRequest(BaseModel):
    weights: Dict[str, float]


class RoutingWeightsResponse(BaseModel):
    weights: Dict[str, float]
    updated_at: datetime


class TenantPolicyRequest(BaseModel):
    tenant_id: str
    model: Optional[str] = None
    fallback_model: Optional[str] = None
    weights: Optional[Dict[str, float]] = None


class TenantPolicyResponse(BaseModel):
    tenant_id: str
    model: Optional[str] = None
    fallback_model: Optional[str] = None
    weights: Optional[Dict[str, float]] = None
    updated_at: datetime


class RoutingConfigUpdateRequest(BaseModel):
    sticky_sessions: Optional[bool] = None
    max_retries: Optional[int] = None


class RoutingConfigResponse(BaseModel):
    routes: Dict[str, str]
    fallbacks: Dict[str, str]
    weights: Dict[str, float]
    tenant_policy_count: int
    sticky_sessions: bool
    max_retries: int
    updated_at: datetime


class AbTestRequest(BaseModel):
    name: str
    model_a: str
    model_b: str
    traffic_split: float = 0.5


class AbTestResponse(BaseModel):
    id: str
    name: str
    model_a: str
    model_b: str
    traffic_split: float
    status: str
    created_at: datetime


class CircuitBreakerRequest(BaseModel):
    model: str
    action: CircuitState = "open"


class CircuitBreakerResponse(BaseModel):
    model: str
    state: CircuitState
    updated_at: datetime