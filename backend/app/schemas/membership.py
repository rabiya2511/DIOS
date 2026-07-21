"""
Pydantic schemas for the Membership domain (invite/accept/reject flow).
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr


class MembershipInviteRequest(BaseModel):
    org_id: str
    email: EmailStr
    role: str = "member"


class MembershipActionRequest(BaseModel):
    membership_id: str


class MembershipRoleUpdateRequest(BaseModel):
    membership_id: str
    role: str


class MembershipOut(BaseModel):
    id: str
    org_id: str
    email: str
    role: str
    status: str
    invited_by: str
    created_at: datetime