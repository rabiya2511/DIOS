"""
Schemas for the Events & Metrics domain (Analytics APIs blueprint).
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class EventCreateRequest(BaseModel):
    name: str
    payload: dict[str, Any] = {}


class EventResponse(BaseModel):
    id: str
    name: str
    payload: dict[str, Any]
    actor_email: str
    timestamp: datetime


class SystemMetricsResponse(BaseModel):
    cpu_usage_percent: float
    memory_usage_percent: float
    disk_usage_percent: float
    uptime_seconds: int
    generated_at: datetime


class BusinessMetricsResponse(BaseModel):
    active_users: int
    total_events_logged: int
    total_conversations: int
    generated_at: datetime


class RealtimeMetricsResponse(BaseModel):
    requests_per_second: float
    active_connections: int
    error_rate_percent: float
    generated_at: datetime