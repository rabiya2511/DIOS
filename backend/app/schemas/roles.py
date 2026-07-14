"""
Pydantic schemas for the Roles & Permissions domain.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class RoleCreateRequest(BaseModel):
    name: str
    permissions: list[str]


class RoleUpdateRequest(BaseModel):
    name: Optional[str] = None
    permissions: Optional[list[str]] = None


class RoleOut(BaseModel):
    id: str
    name: str
    permissions: list[str]
    created_at: datetime


class PermissionOut(BaseModel):
    key: str
    description: str