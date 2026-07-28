"""
Pydantic schemas for the AI Chat: Chat Sessions domain.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ChatCreateRequest(BaseModel):
    title: str


class ChatUpdateRequest(BaseModel):
    title: Optional[str] = None


class ChatOut(BaseModel):
    id: str
    title: str
    owner_email: str
    status: str
    created_at: datetime
    updated_at: datetime


class ChatIdBodyRequest(BaseModel):
    chat_id: str


class ChatShareResponse(BaseModel):
    share_token: str
    chat_id: str
    shared_by: str
    created_at: datetime


class ChatExportOut(BaseModel):
    id: str
    title: str
    owner_email: str
    status: str
    exported_at: datetime


class ChatImportRequest(BaseModel):
    title: str