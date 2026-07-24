"""
Pydantic schemas for the Templates & Automation domain.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class TemplateCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None


class TemplateOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    creator_email: str
    created_at: datetime


class CreateFromTemplateRequest(BaseModel):
    new_name: Optional[str] = None


class ProjectExportOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    owner_email: str
    status: str
    exported_at: datetime


class ProjectImportRequest(BaseModel):
    name: str
    description: Optional[str] = None


class ProjectDuplicateRequest(BaseModel):
    new_name: Optional[str] = None