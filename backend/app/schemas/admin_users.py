"""
Pydantic schemas for the User & Access Administration domain.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class AdminUserOut(BaseModel):
    id: str
    email: str
    full_name: str
    created_at: datetime
    is_admin: bool
    suspended: bool


class AdminUserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    is_admin: Optional[bool] = None


class AdminUserActionRequest(BaseModel):
    email: EmailStr


class AdminResetPasswordResponse(BaseModel):
    message: str
    reset_token: str  # TEMP: normally emailed, not returned


class AdminUserActivityOut(BaseModel):
    email: str
    success: bool
    ip: str
    timestamp: datetime