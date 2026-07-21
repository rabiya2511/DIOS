"""
Pydantic schemas for the Activity domain.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ActivityEntryOut(BaseModel):
    type: str
    detail: str
    timestamp: datetime


class UsageOut(BaseModel):
    total_logins: int
    total_audit_actions: int
    account_age_days: int


class LoginHistoryEntryOut(BaseModel):
    success: bool
    ip: str
    timestamp: datetime


class AuditEntryOut(BaseModel):
    actor_email: str
    action: str
    timestamp: datetime


class NotificationOut(BaseModel):
    id: str
    message: str
    read: bool
    created_at: datetime


class ExportRequest(BaseModel):
    export_type: str = "activity"

class ExportOut(BaseModel):
    id: str
    type: str
    status: str
    created_at: datetime
 
    