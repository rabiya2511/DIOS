"""
Schemas for the Agent Lifecycle group of the Agents & Planning APIs
blueprint.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Literal

from pydantic import BaseModel, EmailStr, Field

AgentStatus = Literal["active", "archived", "disabled"]


class AgentCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    model_id: str = Field(..., description="Which model this agent runs on")
    instructions: str = Field(..., description="System instructions / persona for the agent")
    tools: List[str] = Field(default_factory=list, description="Tool names this agent is allowed to invoke")
    config: Dict[str, Any] = Field(default_factory=dict)


class AgentUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    model_id: Optional[str] = None
    instructions: Optional[str] = None
    tools: Optional[List[str]] = None
    config: Optional[Dict[str, Any]] = None


class AgentResponse(BaseModel):
    id: str
    owner_email: EmailStr
    name: str
    description: Optional[str] = None
    model_id: str
    instructions: str
    tools: List[str]
    config: Dict[str, Any]
    status: AgentStatus
    created_at: datetime
    updated_at: datetime


class AgentListResponse(BaseModel):
    total: int
    items: List[AgentResponse]


class AgentIdBodyRequest(BaseModel):
    agent_id: str


class AgentCloneRequest(BaseModel):
    agent_id: str
    new_name: Optional[str] = None