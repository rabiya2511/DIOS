"""
Schemas for the Alerts domain (Analytics APIs blueprint).
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AlertCreateRequest(BaseModel):
    name: str
    condition: str  # e.g. "cpu_usage_percent > 80"
    severity: str = "warning"  # "info" | "warning" | "critical"


class AlertUpdateRequest(BaseModel):
    status: Optional[str] = None  # "active" | "acknowledged" | "resolved"
    severity: Optional[str] = None


class AlertResponse(BaseModel):
    id: str
    name: str
    condition: str
    severity: str
    status: str
    owner_email: str
    created_at: datetime
    updated_at: datetime


class AlertHistoryEntry(BaseModel):
    alert_id: str
    action: str
    detail: str
    actor_email: str
    timestamp: datetime