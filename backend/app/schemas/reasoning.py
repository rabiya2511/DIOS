"""
Schemas for the Reasoning group of the Agents & Planning APIs blueprint.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Literal

from pydantic import BaseModel, EmailStr, Field

SessionStatus = Literal["active", "completed", "reset"]
ReasoningStepType = Literal["thought", "action", "observation", "reflection"]


class ReasoningStartRequest(BaseModel):
    goal: str
    agent_id: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)


class ReasoningStep(BaseModel):
    step_number: int
    step_type: ReasoningStepType
    content: str
    created_at: datetime


class ReasoningSessionResponse(BaseModel):
    id: str
    owner_email: EmailStr
    goal: str
    agent_id: Optional[str] = None
    status: SessionStatus
    steps: List[ReasoningStep]
    reset_count: int
    context: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ReasoningSessionIdBodyRequest(BaseModel):
    session_id: str


class ReasoningStepRequest(BaseModel):
    session_id: str
    content: str
    step_type: ReasoningStepType = "thought"


class ReasoningReflectRequest(BaseModel):
    session_id: str
    content: str


class ReasoningEvaluateResponse(BaseModel):
    session_id: str
    step_count: int
    verdict: Literal["on_track", "needs_more_steps", "stuck"]
    notes: str
    evaluated_at: datetime


class ReasoningExplainResponse(BaseModel):
    session_id: str
    explanation: str
    explained_at: datetime


class ReasoningLogEntry(BaseModel):
    session_id: str
    step_number: int
    step_type: ReasoningStepType
    content: str
    created_at: datetime


class ReasoningLogListResponse(BaseModel):
    total: int
    items: List[ReasoningLogEntry]


class ReasoningMetricsResponse(BaseModel):
    total_sessions: int
    active_sessions: int
    completed_sessions: int
    total_steps: int
    avg_steps_per_session: float