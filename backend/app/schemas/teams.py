"""
Pydantic schemas for the Teams domain.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class TeamCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None


class TeamUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class TeamResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    creator_email: str
    created_at: datetime


class TeamMemberAddRequest(BaseModel):
    email: EmailStr


class TeamMemberResponse(BaseModel):
    email: str


class TeamPermissionGrantRequest(BaseModel):
    key: str


class TeamPermissionResponse(BaseModel):
    key: str
    granted_at: datetime


class TeamMemberBodyRequest(BaseModel):
    team_id: str
    email: EmailStr