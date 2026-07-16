"""
Pydantic schemas for the Policies domain (Authorization APIs blueprint).
A policy is an IAM-style rule: effect (allow/deny) applied to a
resource + action, with optional conditions. Policies have a
draft -> published lifecycle with version snapshots for rollback.
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

Effect = Literal["allow", "deny"]
Status = Literal["draft", "published"]


class PolicyCreateRequest(BaseModel):
    name: str
    description: str | None = None
    effect: Effect
    resource: str
    action: str
    conditions: dict[str, Any] = {}


class PolicyUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    effect: Effect | None = None
    resource: str | None = None
    action: str | None = None
    conditions: dict[str, Any] | None = None


class PolicyResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    effect: Effect
    resource: str
    action: str
    conditions: dict[str, Any]
    status: Status
    version: int
    created_at: datetime
    updated_at: datetime


class PolicyTestRequest(BaseModel):
    effect: Effect
    resource: str
    action: str
    conditions: dict[str, Any] = {}
    # the sample request to evaluate against
    request_resource: str
    request_action: str
    request_context: dict[str, Any] = {}


class PolicyTestResponse(BaseModel):
    matched: bool
    effect: Effect | None = None  # the resulting effect if matched


class PolicyValidateRequest(BaseModel):
    effect: Effect
    resource: str
    action: str
    conditions: dict[str, Any] = {}


class PolicyValidateResponse(BaseModel):
    valid: bool
    errors: list[str] = []


class PolicyHistoryEntry(BaseModel):
    policy_id: str
    action: Literal["created", "updated", "deleted", "published", "rolled_back"]
    version: int | None = None
    timestamp: datetime


class PolicyPublishRequest(BaseModel):
    id: str


class PolicyRollbackRequest(BaseModel):
    id: str
    version: int