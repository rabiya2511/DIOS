"""
Schemas for the Tasks group of the Agents & Planning APIs blueprint.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Literal

from pydantic import BaseModel, EmailStr, Field

TaskStatus = Literal["pending", "assigned", "completed", "failed"]


class TaskCreateRequest(BaseModel):
    title: str
    description: Optional[str] = None
    plan_id: Optional[str] = Field(None, description="Plan this task was generated from, if any")
    agent_id: Optional[str] = Field(None, description="Agent this task is pre-assigned to, if any")
    priority: int = Field(0, ge=0, le=10, description="Higher number = higher priority")
    config: Dict[str, Any] = Field(default_factory=dict)


class TaskUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    plan_id: Optional[str] = None
    agent_id: Optional[str] = None
    priority: Optional[int] = Field(None, ge=0, le=10)
    config: Optional[Dict[str, Any]] = None


class TaskResponse(BaseModel):
    id: str
    owner_email: EmailStr
    title: str
    description: Optional[str] = None
    plan_id: Optional[str] = None
    agent_id: Optional[str] = None
    priority: int
    status: TaskStatus
    result: Optional[str] = None
    retry_count: int
    config: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class TaskListResponse(BaseModel):
    total: int
    items: List[TaskResponse]


class TaskIdBodyRequest(BaseModel):
    task_id: str


class TaskAssignRequest(BaseModel):
    task_id: str
    agent_id: str


class TaskCompleteRequest(BaseModel):
    task_id: str
    result: Optional[str] = None