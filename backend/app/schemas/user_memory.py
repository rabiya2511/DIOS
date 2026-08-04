"""
Pydantic schemas for the User Memory domain (Memory APIs blueprint).
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class UserMemoryUpsertRequest(BaseModel):
    content: str
    memory_type: str = "profile"


class UserMemoryOut(BaseModel):
    user_id: str
    content: str
    memory_type: str
    managed_by: str
    created_at: datetime
    updated_at: datetime


class UserMemoryImportEntry(BaseModel):
    user_id: str
    content: str
    memory_type: str = "profile"


class UserMemoryImportRequest(BaseModel):
    entries: List[UserMemoryImportEntry]


class UserMemoryImportResponse(BaseModel):
    imported_count: int
    profiles: List[UserMemoryOut]


class UserMemoryExportResponse(BaseModel):
    profiles: List[UserMemoryOut]