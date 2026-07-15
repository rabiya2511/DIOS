"""
Pydantic schemas for the System Operations admin domain.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SystemOperationResponse(BaseModel):
    message: str
    timestamp: datetime


class SystemHealthOut(BaseModel):
    status: str
    uptime_seconds: float
    database: str


class SystemVersionOut(BaseModel):
    api_version: str
    build: str
    environment: str


class MaintenanceRequest(BaseModel):
    enabled: bool
    message: Optional[str] = None


class MaintenanceResponse(BaseModel):
    maintenance_mode: bool
    message: Optional[str] = None