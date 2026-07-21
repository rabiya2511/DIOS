"""
Pydantic schemas for the Alerts domain (Monitoring APIs blueprint).
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

Severity = Literal["info", "warning", "critical"]
AlertStatus = Literal["active", "acknowledged", "resolved"]


class AlertCreateRequest(BaseModel):
    title: str
    description: str | None = None
    severity: Severity = "warning"


class AlertUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    status: AlertStatus | None = None


class AlertResponse(BaseModel):
    id: str
    title: str
    description: str | None = None
    severity: Severity
    status: AlertStatus
    created_at: datetime
    updated_at: datetime


class AlertHistoryEntry(BaseModel):
    alert_id: str
    status: AlertStatus
    timestamp: datetime