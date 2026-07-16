"""
Pydantic schemas for the Access Evaluation domain (Authorization APIs blueprint).
Ties together Roles, Permissions, Role Assignments, and Policies into
real allow/deny decisions.
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


class AccessCheckRequest(BaseModel):
    user_id: str
    resource: str
    action: str
    context: dict[str, Any] = {}


class AccessCheckResponse(BaseModel):
    allowed: bool
    reason: str


class AccessBulkCheckRequest(BaseModel):
    checks: list[AccessCheckRequest]


class AccessBulkCheckResult(BaseModel):
    user_id: str
    resource: str
    action: str
    allowed: bool
    reason: str


class AccessBulkCheckResponse(BaseModel):
    results: list[AccessBulkCheckResult]


class MatchedPermission(BaseModel):
    role_id: str
    role_name: str
    permission_key: str


class MatchedPolicy(BaseModel):
    policy_id: str
    policy_name: str
    effect: Literal["allow", "deny"]


class AccessEvaluateResponse(BaseModel):
    allowed: bool
    reason: str
    matched_permissions: list[MatchedPermission]
    matched_policies: list[MatchedPolicy]


class AccessSimulateRequest(BaseModel):
    resource: str
    action: str
    # hypothetical inputs — not looked up from real data
    hypothetical_permissions: list[str] = []  # e.g. ["users:read", "*"]
    context: dict[str, Any] = {}


class AccessSimulateResponse(BaseModel):
    allowed: bool
    reason: str


class EffectivePermissionsResponse(BaseModel):
    user_id: str
    permissions: list[str]


class AccessResourcesResponse(BaseModel):
    resources: list[str]


class AccessHistoryEntry(BaseModel):
    user_id: str
    resource: str
    action: str
    allowed: bool
    reason: str
    timestamp: datetime


class AccessCacheEntry(BaseModel):
    user_id: str
    resource: str
    action: str
    allowed: bool
    cached_at: datetime


class AccessCacheResponse(BaseModel):
    entries: list[AccessCacheEntry]


class AccessCacheClearResponse(BaseModel):
    cleared: int