"""
Pydantic schemas for the User CRUD domain (User Management APIs blueprint).
Admin-facing user management, distinct from self-service /auth/register.
Reuses the same users_db as the rest of the app.
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserCreateRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str


class UserUpdateRequest(BaseModel):
    full_name: str | None = None
    email_verified: bool | None = None


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    email_verified: bool = False
    created_at: datetime


class UserSearchRequest(BaseModel):
    query: str  # substring match against email or full_name


class UserBulkImportRequest(BaseModel):
    users: list[UserCreateRequest]


class UserBulkImportResult(BaseModel):
    email: str
    success: bool
    detail: str | None = None


class UserBulkImportResponse(BaseModel):
    results: list[UserBulkImportResult]


class UserBulkExportResponse(BaseModel):
    users: list[UserResponse]