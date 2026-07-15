"""
Pydantic schemas for the Permissions domain (Authorization APIs blueprint).
A permission key is formatted "resource:action" (e.g. "users:read").
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class PermissionCreateRequest(BaseModel):
    key: str  # e.g. "users:read"
    description: str


class PermissionUpdateRequest(BaseModel):
    description: str | None = None


class PermissionResponse(BaseModel):
    id: str
    key: str
    resource: str
    action: str
    description: str
    created_at: datetime
    updated_at: datetime


class PermissionImportRequest(BaseModel):
    permissions: list[PermissionCreateRequest]


class PermissionImportResponse(BaseModel):
    imported: int
    skipped: int  # keys that already existed


class PermissionExportResponse(BaseModel):
    permissions: list[PermissionResponse]


class PermissionCatalogGroup(BaseModel):
    resource: str
    permissions: list[PermissionResponse]


class PermissionValidateRequest(BaseModel):
    key: str


class PermissionValidateResponse(BaseModel):
    valid: bool
    key: str


class PermissionHistoryEntry(BaseModel):
    permission_id: str
    key: str
    action: Literal["created", "updated", "deleted"]
    timestamp: datetime