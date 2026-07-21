"""
Pydantic schemas for the Notification Management domain
(Notifications APIs blueprint).
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr

NotificationType = Literal["info", "warning", "success", "error"]


class NotificationCreateRequest(BaseModel):
    recipient_email: EmailStr
    title: str
    body: str
    type: NotificationType = "info"


class NotificationUpdateRequest(BaseModel):
    title: str | None = None
    body: str | None = None
    read: bool | None = None


class NotificationResponse(BaseModel):
    id: str
    recipient_email: EmailStr
    title: str
    body: str
    type: NotificationType
    read: bool
    created_at: datetime