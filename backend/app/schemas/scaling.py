"""
Pydantic schemas for the Scaling & Availability domain
(Deployment & Infrastructure APIs blueprint).
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AutoscalingConfigRequest(BaseModel):
    enabled: bool = True
    min_instances: int = 2
    max_instances: int = 10
    target_cpu_percent: int = 70


class AutoscalingStatusResponse(BaseModel):
    enabled: bool
    min_instances: int
    max_instances: int
    target_cpu_percent: int
    current_instances: int
    updated_at: datetime


class FailoverRequest(BaseModel):
    target_region: Optional[str] = None


class FailoverResponse(BaseModel):
    id: str
    from_region: str
    to_region: str
    status: str
    triggered_by: str
    triggered_at: datetime


class HealthResponse(BaseModel):
    status: str
    checked_at: datetime


class ReadinessResponse(BaseModel):
    ready: bool
    checked_at: datetime


class LivenessResponse(BaseModel):
    alive: bool
    checked_at: datetime