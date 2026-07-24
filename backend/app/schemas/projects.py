"""
Pydantic schemas for the Project Management domain
(Projects & Workspace APIs blueprint).
"""

from datetime import datetime
from typing import Optional, Literal

from pydantic import BaseModel

ProjectStatus = Literal["active", "archived"]


class ProjectCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None


class ProjectUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    owner_email: str
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime


class ProjectIdBodyRequest(BaseModel):
    project_id: str


class ProjectCloneRequest(BaseModel):
    project_id: str
    new_name: Optional[str] = None