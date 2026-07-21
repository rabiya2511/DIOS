"""
Pydantic schemas for the Health & Status domain (Monitoring APIs blueprint).
STUBBED: readiness/liveness always report healthy — a real version would
check DB connectivity, downstream dependencies, deadlocks, etc.
"""

from datetime import datetime

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime


class StatusResponse(BaseModel):
    status: str
    uptime_seconds: float
    version: str


class ReadinessResponse(BaseModel):
    ready: bool
    checks: dict[str, bool]


class LivenessResponse(BaseModel):
    alive: bool