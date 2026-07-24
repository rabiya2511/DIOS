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
class WorkspaceSettingsOut(BaseModel):
    workspace_id: str
    settings: dict


class WorkspaceSettingsUpdateRequest(BaseModel):
    settings: dict


class WorkspaceBrandingOut(BaseModel):
    workspace_id: str
    logo_url: str = ""
    primary_color: str = "#000000"
    name_override: Optional[str] = None


class WorkspaceBrandingUpdateRequest(BaseModel):
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    name_override: Optional[str] = None


class WorkspacePreferencesOut(BaseModel):
    workspace_id: str
    preferences: dict


class WorkspacePreferencesUpdateRequest(BaseModel):
    preferences: dict


class WorkspaceActivityEntryOut(BaseModel):
    action: str
    actor_email: str
    timestamp: datetime