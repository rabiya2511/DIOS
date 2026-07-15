"""
Pydantic schemas for the Security & Audit admin domain.
"""

from datetime import datetime

from pydantic import BaseModel


class AdminSecurityEventOut(BaseModel):
    email: str
    event: str
    detail: str
    timestamp: datetime


class RotateKeysResponse(BaseModel):
    message: str
    timestamp: datetime


class RevokeSessionsResponse(BaseModel):
    message: str
    sessions_revoked: int
    timestamp: datetime


class AdminAuditLogOut(BaseModel):
    actor_email: str
    action: str
    timestamp: datetime


class AdminAccessHistoryOut(BaseModel):
    email: str
    success: bool
    ip: str
    timestamp: datetime


class ComplianceReportOut(BaseModel):
    generated_at: datetime
    total_users: int
    total_admins: int
    suspended_users: int
    total_audit_entries: int
    total_login_attempts: int