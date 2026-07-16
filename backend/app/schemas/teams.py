"""
Pydantic schemas for the Team Authorization domain (Authorization APIs
blueprint). Teams are a standalone entity with flat membership (no
per-member roles) and their own granted-permission set, same pattern
as Organization Authorization's permission grants.
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr


class TeamCreateRequest(BaseModel):
    name: str
    description: str | None = None


class TeamUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None


class TeamResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    creator_email: EmailStr
    created_at: datetime


class TeamMemberAddRequest(BaseModel):
    email: EmailStr


class TeamMemberResponse(BaseModel):
    email: EmailStr


class TeamPermissionGrantRequest(BaseModel):
    key: str


class TeamPermissionResponse(BaseModel):
    key: str
    granted_at: datetime
   