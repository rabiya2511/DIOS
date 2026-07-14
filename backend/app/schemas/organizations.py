"""
Pydantic schemas for the Organizations domain.
STUBBED: invite doesn't send a real email — it adds the member directly.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr

Role = Literal["owner", "admin", "member"]


class OrganizationCreateRequest(BaseModel):
    name: str


class OrganizationResponse(BaseModel):
    id: str
    name: str
    owner_email: EmailStr
    role: Role  # the current user's role in this org
    created_at: datetime


class OrganizationInviteRequest(BaseModel):
    org_id: str
    email: EmailStr
    role: Role = "member"


class MemberRoleUpdateRequest(BaseModel):
    org_id: str
    email: EmailStr
    role: Role


class MemberRemoveRequest(BaseModel):
    org_id: str
    email: EmailStr


class MemberItem(BaseModel):
    email: EmailStr
    role: Role


class MembersResponse(BaseModel):
    org_id: str
    members: list[MemberItem]