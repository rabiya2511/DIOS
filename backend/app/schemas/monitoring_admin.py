"""
Pydantic schemas for the Administration domain (Monitoring APIs
blueprint) — config, cache clear, audit, test trigger.
"""

from datetime import datetime

from pydantic import BaseModel


class MonitoringConfigResponse(BaseModel):
    log_retention_days: int
    alert_threshold_cpu_percent: float
    tracing_sample_rate: float


class MonitoringConfigUpdateRequest(BaseModel):
    log_retention_days: int | None = None
    alert_threshold_cpu_percent: float | None = None
    tracing_sample_rate: float | None = None


class CacheClearResponse(BaseModel):
    cleared_entries: int


class MonitoringAuditEntry(BaseModel):
    actor_email: str
    action: str
    timestamp: datetime


class MonitoringTestResponse(BaseModel):
    log_id: str
    alert_id: str
    trace_id: str
    detail: str