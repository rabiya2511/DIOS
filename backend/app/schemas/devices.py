"""
Pydantic schemas for the Devices domain.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DeviceRegisterRequest(BaseModel):
    name: str


class DeviceTrustRequest(BaseModel):
    device_id: str
    trusted: bool


class DeviceOut(BaseModel):
    id: str
    name: str
    trusted: bool
    active: bool
    created_at: datetime
    last_active_at: datetime


class DeviceLogoutRequest(BaseModel):
    device_id: str