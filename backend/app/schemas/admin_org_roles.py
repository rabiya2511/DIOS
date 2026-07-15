"""
Pydantic schemas for the Organization & Roles admin domain.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AdminOrganizationOut(BaseModel):
    id: str
    name: str
    owner_email: str
    created_at: datetime


class AdminOrganizationUpdateRequest(BaseModel):
    name: Optional[str] = None
    owner_email: Optional[str] = None


class AdminRoleOut(BaseModel):
    id: str
    name: str
    permissions: list[str]
    created_at: datetime


class AdminRoleCreateRequest(BaseModel):
    name: str
    permissions: list[str]


class AdminPermissionUpdateRequest(BaseModel):
    key: str
    description: str


class AdminPermissionOut(BaseModel):
    key: str
    description: str


class AdminPoliciesOut(BaseModel):
    password_min_length: int
    password_require_uppercase: bool
    password_require_number: bool
    session_timeout_minutes: int
    mfa_required_for_admins: bool