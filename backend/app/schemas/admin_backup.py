"""
Pydantic schemas for the Backup & Monitoring admin domain.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class BackupResponse(BaseModel):
    id: str
    message: str
    created_at: datetime


class RestoreRequest(BaseModel):
    backup_id: str


class RestoreResponse(BaseModel):
    message: str
    backup_id: str
    restored_at: datetime


class MetricsOut(BaseModel):
    total_users: int
    total_organizations: int
    total_api_keys: int
    uptime_seconds: float


class LogEntryOut(BaseModel):
    level: str
    message: str
    timestamp: str


class AlertOut(BaseModel):
    id: str
    severity: str
    message: str
    active: bool


class AdminSettingsOut(BaseModel):
    backup_frequency_hours: int
    log_retention_days: int
    alert_email: str


class AdminSettingsUpdateRequest(BaseModel):
    backup_frequency_hours: Optional[int] = None
    log_retention_days: Optional[int] = None
    alert_email: Optional[str] = None