"""
Schemas for the Tools group of the Agents & Planning APIs blueprint.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Literal

from pydantic import BaseModel, EmailStr, Field

ToolStatus = Literal["active", "disabled"]
InvocationStatus = Literal["success", "failed", "unauthorized"]


class ToolRegisterRequest(BaseModel):
    name: str
    description: Optional[str] = None
    tool_type: str = Field(..., description="e.g. 'api', 'function', 'webhook'")
    endpoint: Optional[str] = Field(None, description="URL or identifier the tool invokes")
    auth_required: bool = False
    config: Dict[str, Any] = Field(default_factory=dict)


class ToolUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    tool_type: Optional[str] = None
    endpoint: Optional[str] = None
    auth_required: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None


class ToolResponse(BaseModel):
    id: str
    owner_email: EmailStr
    name: str
    description: Optional[str] = None
    tool_type: str
    endpoint: Optional[str] = None
    auth_required: bool
    status: ToolStatus
    authorized_agent_ids: List[str]
    config: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ToolListResponse(BaseModel):
    total: int
    items: List[ToolResponse]


class ToolIdBodyRequest(BaseModel):
    tool_id: str


class ToolAuthorizeRequest(BaseModel):
    tool_id: str
    agent_id: str = Field(..., description="Agent being granted permission to invoke this tool")


class ToolInvokeRequest(BaseModel):
    tool_id: str
    agent_id: Optional[str] = Field(
        None, description="Agent invoking on the owner's behalf; required if the caller isn't the tool owner"
    )
    params: Dict[str, Any] = Field(default_factory=dict)


class ToolInvokeResponse(BaseModel):
    invocation_id: str
    tool_id: str
    status: InvocationStatus
    output: Optional[str] = None
    invoked_at: datetime


class ToolTestRequest(BaseModel):
    tool_id: str
    params: Dict[str, Any] = Field(default_factory=dict)


class ToolTestResponse(BaseModel):
    tool_id: str
    status: Literal["success", "failed"]
    output: Optional[str] = None
    tested_at: datetime


class ToolHistoryEntry(BaseModel):
    invocation_id: str
    tool_id: str
    agent_id: Optional[str] = None
    invoker_email: EmailStr
    status: InvocationStatus
    params: Dict[str, Any]
    output: Optional[str] = None
    invoked_at: datetime


class ToolHistoryListResponse(BaseModel):
    total: int
    items: List[ToolHistoryEntry]