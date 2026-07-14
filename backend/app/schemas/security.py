"""
Pydantic schemas for the Security & Audit domain.
"""

from datetime import datetime

from pydantic import BaseModel


class SecurityEventOut(BaseModel):
    event: str
    detail: str
    timestamp: datetime


class LoginHistoryOut(BaseModel):
    success: bool
    ip: str
    timestamp: datetime


class AuditLogOut(BaseModel):
    actor_email: str
    action: str
    timestamp: datetime