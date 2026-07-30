"""
Pydantic schemas for the Administration domain (Agents & Planning APIs
blueprint). Reuses agents_db from agent_lifecycle.py.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AgentIdBodyRequest(BaseModel):
    agent_id: str


class AgentEnableResponse(BaseModel):
    agent_id: str
    status: str


class AgentConfigUpdateRequest(BaseModel):
    agent_id: str
    config: dict[str, Any]


class AgentConfigResponse(BaseModel):
    agent_id: str
    config: dict[str, Any]


class AgentReindexResponse(BaseModel):
    reindexed_count: int
    completed_at: datetime


class AgentReloadResponse(BaseModel):
    agent_id: str
    reloaded: bool
    reloaded_at: datetime


class AgentPolicyCreateRequest(BaseModel):
    agent_id: str
    policy: dict[str, Any]


class AgentPolicyResponse(BaseModel):
    id: str
    agent_id: str
    policy: dict[str, Any]
    created_at: datetime


class AgentPolicyListResponse(BaseModel):
    total: int
    items: list[AgentPolicyResponse]