"""
Pydantic schemas for the Organization Authorization domain
(Authorization APIs blueprint). Extends the existing Organizations
domain with path-scoped membership ops, org-level permission grants,
audit log, access summary, and ownership transfer.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr

Role = Literal["owner", "admin", "member"]


class OrgMemberAddRequest(BaseModel):
    email: EmailStr
    role: Role = "member"


class OrgMemberResponse(BaseModel):
    email: EmailStr
    role: Role


class OrgMemberRoleUpdateRequest(BaseModel):
    role: Role


class OrgPermissionGrantRequest(BaseModel):
    key: str  # must match an existing permission key, e.g. "users:read"


class OrgPermissionResponse(BaseModel):
    key: str
    granted_at: datetime


class OrgAuditEntry(BaseModel):
    org_id: str
    action: str
    actor_email: str
    detail: str
    timestamp: datetime


class OrgAccessResponse(BaseModel):
    org_id: str
    members: list[OrgMemberResponse]
    granted_permissions: list[str]


class OrgTransferOwnerRequest(BaseModel):
    new_owner_email: EmailStr