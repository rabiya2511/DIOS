"""
Pydantic schemas for the Agents domain (AI Chat APIs blueprint).

Everything here describes a SIMULATED agent — see router docstring.
No real autonomous execution, tool calling, or planning happens.
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel

AgentStatus = Literal["idle", "running", "stopped", "completed"]


class AgentCreateRequest(BaseModel):
    chat_id: str
    name: str
    goal: str


class AgentOut(BaseModel):
    id: str
    chat_id: str
    name: str
    goal: str
    status: AgentStatus
    owner_email: str
    created_at: datetime


class AgentIdRequest(BaseModel):
    agent_id: str


class AgentRunResponse(BaseModel):
    run_id: str
    agent_id: str
    status: AgentStatus
    started_at: datetime


class AgentStopResponse(BaseModel):
    agent_id: str
    status: AgentStatus
    stopped_at: datetime


class AgentStatusResponse(BaseModel):
    agent_id: str
    status: AgentStatus
    active_run_id: Optional[str] = None
    task_count: int
    completed_task_count: int


class AgentToolRequest(BaseModel):
    agent_id: str
    tool_name: str
    tool_input: Dict[str, Any] = {}


class AgentToolResponse(BaseModel):
    id: str
    agent_id: str
    tool_name: str
    result: str
    created_at: datetime


class AgentPlannerResponse(BaseModel):
    agent_id: str
    plan_steps: List[str]
    created_at: datetime


class AgentTaskOut(BaseModel):
    id: str
    description: str
    status: Literal["pending", "completed"]
    created_at: datetime


class AgentTasksResponse(BaseModel):
    agent_id: str
    tasks: List[AgentTaskOut]


class AgentHistoryEntry(BaseModel):
    id: str
    agent_id: str
    event: str
    detail: str
    timestamp: datetime


class AgentHistoryResponse(BaseModel):
    agent_id: str
    history: List[AgentHistoryEntry]