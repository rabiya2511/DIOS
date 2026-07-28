"""
Pydantic schemas for the Deployment & Infrastructure: Monitoring & Administration domain.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class InfraMetricsOut(BaseModel):
    total_deployments: int
    healthy_nodes: int
    total_nodes: int
    uptime_percent: float


class InfraLogEntryOut(BaseModel):
    level: str
    message: str
    timestamp: str


class InfraAuditEntryOut(BaseModel):
    actor_email: str
    action: str
    timestamp: datetime


class InfraConfigOut(BaseModel):
    auto_scaling_enabled: bool
    max_nodes: int
    region: str


class InfraConfigUpdateRequest(BaseModel):
    auto_scaling_enabled: Optional[bool] = None
    max_nodes: Optional[int] = None
    region: Optional[str] = None


class InfraBackupOut(BaseModel):
    id: str
    message: str
    created_at: datetime


class InfraRestoreRequest(BaseModel):
    backup_id: str


class InfraRestoreOut(BaseModel):
    backup_id: str
    message: str
    restored_at: datetime