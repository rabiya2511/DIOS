"""
Pydantic schemas for the Resource Authorization domain.
"""

from typing import Optional

from pydantic import BaseModel, EmailStr


class ResourceShareRequest(BaseModel):
    resource_id: str
    email: EmailStr
    permission: str = "read"


class ResourceShareOut(BaseModel):
    id: str
    resource_id: str
    email: str
    permission: str


class ResourcePermissionsOut(BaseModel):
    resource_id: str
    owner_email: Optional[str] = None
    shares: list[ResourceShareOut]


class ResourcePermissionsUpdateRequest(BaseModel):
    email: EmailStr
    permission: str


class ResourceOwnerRequest(BaseModel):
    new_owner_email: EmailStr


class ResourceAccessOut(BaseModel):
    resource_id: str
    owner_email: Optional[str] = None
    locked: bool
    shared_with_count: int


class ResourceLockResponse(BaseModel):
    resource_id: str
    locked: bool


class ResourceInheritRequest(BaseModel):
    parent_resource_id: str


class ResourceRevokeAllResponse(BaseModel):
    resource_id: str
    revoked_count: int