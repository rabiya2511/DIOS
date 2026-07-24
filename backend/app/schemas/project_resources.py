"""
Pydantic schemas for the Project Resources domain
(Projects & Workspace APIs blueprint).

NOTE: These are lightweight, project-scoped resource RECORDS (metadata
only) — not the same thing as the global File & Storage domain
(fileslifecycle.py's files_db). A "file" here is just a name/size/mime_type
attached to a project; it doesn't reference or create an actual entry in
files_db. Wire the two together later if you want project files to be
real files_db entries.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ProjectFileCreateRequest(BaseModel):
    name: str
    size_bytes: int = 0
    mime_type: Optional[str] = None


class ProjectFileOut(BaseModel):
    id: str
    project_id: str
    name: str
    size_bytes: int
    mime_type: Optional[str] = None
    added_by: str
    created_at: datetime


class ProjectDatasetCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    row_count: int = 0


class ProjectDatasetOut(BaseModel):
    id: str
    project_id: str
    name: str
    description: Optional[str] = None
    row_count: int
    added_by: str
    created_at: datetime


class ProjectModelCreateRequest(BaseModel):
    name: str
    framework: Optional[str] = None
    version: str = "1.0"


class ProjectModelOut(BaseModel):
    id: str
    project_id: str
    name: str
    framework: Optional[str] = None
    version: str
    added_by: str
    created_at: datetime