"""
Schemas for File Permissions domain (File & Storage blueprint).
Not to be confused with app/schemas/permissions.py, which covers
Authorization-domain role/permission keys.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class FilePermissionCreateRequest(BaseModel):
    file_id: str
    grantee_email: str
    access_level: str  # "viewer" | "editor" | "owner"


class FilePermissionUpdateRequest(BaseModel):
    access_level: str


class FilePermissionResponse(BaseModel):
    id: str
    file_id: str
    grantee_email: str
    access_level: str
    granted_by_email: str
    created_at: datetime
    updated_at: datetime


class ShareLinkCreateRequest(BaseModel):
    file_id: str
    access_level: Optional[str] = "viewer"
    expires_in_seconds: Optional[int] = 86400


class ShareLinkResponse(BaseModel):
    file_id: str
    link_token: str
    url: str
    access_level: str
    expires_at: datetime


class ShareLinkRevokeRequest(BaseModel):
    file_id: str
    link_token: str


class FileInviteRequest(BaseModel):
    file_id: str
    email: str
    access_level: Optional[str] = "viewer"
    message: Optional[str] = None


class FileInviteResponse(BaseModel):
    file_id: str
    invited_email: str
    access_level: str
    invited_by_email: str
    invited_at: datetime


class PermissionAuditEntry(BaseModel):
    file_id: str
    action: str
    actor_email: str
    target_email: Optional[str] = None
    timestamp: datetime