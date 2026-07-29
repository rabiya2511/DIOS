"""
Schemas for the Planning group of the Agents & Planning APIs blueprint.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Literal

from pydantic import BaseModel, EmailStr, Field

PlanStatus = Literal["draft", "validated", "invalid", "executing", "completed", "failed"]
StepOutcome = Literal["success", "failed", "skipped"]


class PlanStep(BaseModel):
    order: int = Field(..., ge=1, description="1-based execution order of this step")
    description: str = Field(..., description="What this step is meant to accomplish")
    tool_name: Optional[str] = Field(None, description="Tool this step invokes, if any")
    agent_id: Optional[str] = Field(None, description="Agent responsible for this step, if any")
    params: Dict[str, Any] = Field(default_factory=dict)


class PlanCreateRequest(BaseModel):
    name: str
    goal: str = Field(..., description="The objective this plan is trying to achieve")
    description: Optional[str] = None
    agent_id: Optional[str] = Field(None, description="Default agent this plan runs under")
    steps: List[PlanStep] = Field(default_factory=list)
    config: Dict[str, Any] = Field(default_factory=dict)


class PlanUpdateRequest(BaseModel):
    name: Optional[str] = None
    goal: Optional[str] = None
    description: Optional[str] = None
    agent_id: Optional[str] = None
    steps: Optional[List[PlanStep]] = None
    config: Optional[Dict[str, Any]] = None


class PlanResponse(BaseModel):
    id: str
    owner_email: EmailStr
    name: str
    goal: str
    description: Optional[str] = None
    agent_id: Optional[str] = None
    steps: List[PlanStep]
    config: Dict[str, Any]
    status: PlanStatus
    created_at: datetime
    updated_at: datetime


class PlanListResponse(BaseModel):
    total: int
    items: List[PlanResponse]


class PlanIdBodyRequest(BaseModel):
    plan_id: str


# ─── Validate ───

class PlanValidationIssue(BaseModel):
    step_order: Optional[int] = Field(None, description="Null if the issue applies to the plan as a whole")
    message: str


class PlanValidateResponse(BaseModel):
    plan_id: str
    valid: bool
    issues: List[PlanValidationIssue] = Field(default_factory=list)
    validated_at: datetime


# ─── Simulate ───

class SimulatedStepResult(BaseModel):
    order: int
    description: str
    predicted_outcome: StepOutcome
    predicted_output: Optional[str] = None


class PlanSimulateResponse(BaseModel):
    plan_id: str
    simulated_at: datetime
    steps: List[SimulatedStepResult]
    summary: str


# ─── Execute ───

class StepExecutionResult(BaseModel):
    order: int
    description: str
    outcome: StepOutcome
    output: Optional[str] = None
    started_at: datetime
    completed_at: datetime


class PlanExecuteResponse(BaseModel):
    result_id: str
    plan_id: str
    status: Literal["completed", "failed"]
    step_results: List[StepExecutionResult]
    started_at: datetime
    completed_at: datetime


# ─── Results ───

class PlanResultResponse(BaseModel):
    result_id: str
    plan_id: str
    owner_email: EmailStr
    status: Literal["completed", "failed"]
    step_results: List[StepExecutionResult]
    started_at: datetime
    completed_at: datetime


class PlanResultListResponse(BaseModel):
    total: int
    items: List[PlanResultResponse]