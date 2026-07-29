"""
Schemas for the Workflows group of the Agents & Planning APIs blueprint.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Literal

from pydantic import BaseModel, EmailStr, Field

WorkflowStatus = Literal["draft", "active", "archived"]
StepOutcome = Literal["success", "failed", "skipped"]
RunStatus = Literal["completed", "failed"]


class WorkflowStep(BaseModel):
    order: int = Field(..., ge=1)
    name: str
    plan_id: Optional[str] = Field(None, description="Plan this step runs, if any")
    agent_id: Optional[str] = Field(None, description="Agent this step runs under, if any")
    tool_name: Optional[str] = Field(None, description="Tool this step invokes directly, if any")
    params: Dict[str, Any] = Field(default_factory=dict)


class WorkflowCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    steps: List[WorkflowStep] = Field(default_factory=list)
    config: Dict[str, Any] = Field(default_factory=dict)


class WorkflowUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    steps: Optional[List[WorkflowStep]] = None
    config: Optional[Dict[str, Any]] = None


class WorkflowResponse(BaseModel):
    id: str
    owner_email: EmailStr
    name: str
    description: Optional[str] = None
    steps: List[WorkflowStep]
    status: WorkflowStatus
    config: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class WorkflowListResponse(BaseModel):
    total: int
    items: List[WorkflowResponse]


class WorkflowIdBodyRequest(BaseModel):
    workflow_id: str


class WorkflowCloneRequest(BaseModel):
    workflow_id: str
    new_name: Optional[str] = None


class WorkflowStepResult(BaseModel):
    order: int
    name: str
    outcome: StepOutcome
    output: Optional[str] = None
    started_at: datetime
    completed_at: datetime


class WorkflowRunResponse(BaseModel):
    run_id: str
    workflow_id: str
    status: RunStatus
    step_results: List[WorkflowStepResult]
    started_at: datetime
    completed_at: datetime


class WorkflowHistoryEntry(BaseModel):
    run_id: str
    workflow_id: str
    owner_email: EmailStr
    status: RunStatus
    step_results: List[WorkflowStepResult]
    started_at: datetime
    completed_at: datetime


class WorkflowHistoryListResponse(BaseModel):
    total: int
    items: List[WorkflowHistoryEntry]


class WorkflowExportResponse(BaseModel):
    workflow_id: str
    name: str
    description: Optional[str] = None
    steps: List[WorkflowStep]
    config: Dict[str, Any]
    exported_at: datetime
    format: Literal["json"] = "json"