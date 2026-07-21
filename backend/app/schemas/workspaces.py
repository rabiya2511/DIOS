"""
Pydantic schemas for the Workspace domain.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class WorkspaceCreateRequest(BaseModel):
    name: str


class WorkspaceUpdateRequest(BaseModel):
    name: Optional[str] = None


class WorkspaceOut(BaseModel):
    id: str
    name: str
    owner_email: str
    status: str
    created_at: datetime


class WorkspaceSwitchRequest(BaseModel):
    workspace_id: str


class WorkspaceSwitchResponse(BaseModel):
    current_workspace_id: str


class WorkspaceArchiveRequest(BaseModel):
    workspace_id: str