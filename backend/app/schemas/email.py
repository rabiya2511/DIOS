"""
Pydantic schemas for the Email domain (Notifications APIs blueprint).
STUBBED: /email/send doesn't hit a real mail provider — it logs to
email_history_db and returns a simulated "sent" status.
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr


class EmailTemplateCreateRequest(BaseModel):
    name: str
    subject: str
    body: str


class EmailTemplateResponse(BaseModel):
    id: str
    name: str
    subject: str
    body: str
    created_at: datetime


class EmailSendRequest(BaseModel):
    to_email: EmailStr
    subject: str | None = None
    body: str | None = None
    template_id: str | None = None  # if set, pulls subject/body from the template


class EmailSendResponse(BaseModel):
    id: str
    to_email: EmailStr
    subject: str
    body: str
    template_id: str | None = None
    status: str
    sent_at: datetime


class EmailHistoryEntry(BaseModel):
    id: str
    to_email: EmailStr
    subject: str
    body: str
    template_id: str | None = None
    status: str
    sent_at: datetime