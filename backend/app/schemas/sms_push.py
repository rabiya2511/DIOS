"""
Pydantic schemas for the SMS & Push domain (Notifications APIs blueprint).
STUBBED: send endpoints don't hit real SMS/push providers — they log to
history and return a simulated "sent" status.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr

Platform = Literal["ios", "android", "web"]


class SmsSendRequest(BaseModel):
    to_phone: str
    message: str


class SmsSendResponse(BaseModel):
    id: str
    to_phone: str
    message: str
    status: str
    sent_at: datetime


class PushDeviceRegisterRequest(BaseModel):
    device_token: str
    platform: Platform


class PushDeviceResponse(BaseModel):
    id: str
    device_token: str
    platform: Platform
    registered_at: datetime


class PushSendRequest(BaseModel):
    to_email: EmailStr
    title: str
    body: str


class PushSendResponse(BaseModel):
    id: str
    to_email: EmailStr
    title: str
    body: str
    devices_targeted: int
    status: str
    sent_at: datetime