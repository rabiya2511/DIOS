"""
Pydantic schemas for the In-App domain (Notifications APIs blueprint).
Represents an in-app message feed, distinct from the Notification
Management domain's notification-items store.
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr


class InAppSendRequest(BaseModel):
    recipient_email: EmailStr
    title: str
    body: str


class InAppMessageResponse(BaseModel):
    id: str
    recipient_email: EmailStr
    title: str
    body: str
    read: bool
    created_at: datetime


class InAppMarkReadRequest(BaseModel):
    ids: list[str]


class InAppMarkReadResponse(BaseModel):
    marked_read: int
    not_found: int