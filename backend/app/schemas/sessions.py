"""
schemas/sessions.py
-------------------
Pydantic schemas for the Sessions domain.
Import these into your router instead of defining them inline.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


# ---------- Sessions ----------

class SessionOut(BaseModel):
    id: str
    device: Optional[str] = None
    ip: Optional[str] = None
    created_at: datetime
    last_active_at: Optional[datetime] = None
    current: bool = False

    class Config:
        from_attributes = True  # allows creation from ORM objects (Pydantic v2)


# ---------- Devices ----------

class DeviceRegisterIn(BaseModel):
    device_name: str
    device_type: Optional[str] = None  # e.g. "mobile", "desktop", "browser"
    push_token: Optional[str] = None


class DeviceOut(BaseModel):
    id: str
    device_name: str
    device_type: Optional[str] = None
    trusted: bool = False
    registered_at: datetime

    class Config:
        from_attributes = True


class DeviceTrustIn(BaseModel):
    device_id: str
    trusted: bool