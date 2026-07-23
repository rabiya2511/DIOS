"""
Schemas for File Lifecycle domain.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class FileCreateRequest(BaseModel):
    name: str
    folder_id: Optional[str] = None
    size_bytes: Optional[int] = 0
    mime_type: Optional[str] = None


class FileUpdateRequest(BaseModel):
    name: Optional[str] = None
    folder_id: Optional[str] = None


class FileResponse(BaseModel):
    id: str
    name: str
    folder_id: Optional[str] = None
    size_bytes: int = 0
    mime_type: Optional[str] = None
    owner_email: str
    status: str  # "active" | "archived"
    created_at: datetime
    updated_at: datetime


class FileIdBodyRequest(BaseModel):
    file_id: str


class FileCloneRequest(BaseModel):
    file_id: str
    new_name: Optional[str] = None