"""
Schemas for the Agent Execution group of the Agents & Planning APIs
blueprint.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List, Literal

from pydantic import BaseModel, Field

ExecutionStatus = Literal["running", "paused", "stopped", "cancelled", "completed", "failed"]


class AgentRunRequest(BaseModel):
    task: Optional[str] = Field(None, description="Description of what the agent should do")
    input: Dict[str, Any] = Field(default_factory=dict)


class ExecutionActionRequest(BaseModel):
    execution_id: Optional[str] = Field(
        None, description="Target execution; defaults to the agent's most recent execution if omitted"
    )


class ExecutionResponse(BaseModel):
    id: str
    agent_id: str
    owner_email: str
    status: ExecutionStatus
    task: Optional[str] = None
    input: Dict[str, Any]
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: datetime
    ended_at: Optional[datetime] = None
    updated_at: datetime


class ExecutionHistoryResponse(BaseModel):
    total: int
    items: List[ExecutionResponse]


class AgentStatusResponse(BaseModel):
    agent_id: str
    current_status: str = Field(..., description="Latest execution status, or 'idle' if never run")
    latest_execution_id: Optional[str] = None
    checked_at: datetime