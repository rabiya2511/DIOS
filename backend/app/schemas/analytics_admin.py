"""
Schemas for the Administration domain (Analytics APIs blueprint).
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str  # "healthy" | "degraded" | "unhealthy"
    checked_at: datetime


class LogEntry(BaseModel):
    level: str  # "info" | "warning" | "error"
    message: str
    timestamp: datetime


class ConfigUpdateRequest(BaseModel):
    settings: dict[str, Any]


class ConfigResponse(BaseModel):
    settings: dict[str, Any]
    updated_at: datetime


class AuditEntry(BaseModel):
    action: str
    detail: str
    actor_email: str
    timestamp: datetime


class BackupCreateRequest(BaseModel):
    note: Optional[str] = None


class BackupResponse(BaseModel):
    id: str
    note: Optional[str] = None
    status: str  # "completed"
    created_by_email: str
    created_at: datetime