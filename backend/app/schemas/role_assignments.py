"""
Pydantic schemas for the Role Assignments domain (Authorization APIs blueprint).
user_id refers to a user's "id" field (uuid) from users_db, not their email.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class RoleAssignmentCreateRequest(BaseModel):
    user_id: str
    role_id: str


class RoleAssignmentResponse(BaseModel):
    id: str
    user_id: str
    role_id: str
    assigned_at: datetime


class RoleAssignRequest(BaseModel):
    user_id: str


class RoleUnassignRequest(BaseModel):
    user_id: str


class RoleAssignmentBulkCreateRequest(BaseModel):
    assignments: list[RoleAssignmentCreateRequest]


class RoleAssignmentBulkResult(BaseModel):
    user_id: str
    role_id: str
    success: bool
    detail: str | None = None


class RoleAssignmentBulkCreateResponse(BaseModel):
    results: list[RoleAssignmentBulkResult]


class RoleAssignmentBulkDeleteRequest(BaseModel):
    assignment_ids: list[str]


class RoleAssignmentBulkDeleteResponse(BaseModel):
    deleted: int
    not_found: int


class RoleAssignmentHistoryEntry(BaseModel):
    assignment_id: str
    user_id: str
    role_id: str
    action: Literal["assigned", "unassigned"]
    timestamp: datetime