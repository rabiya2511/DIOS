"""
Pydantic schemas for the AI Chat: Messaging domain.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class MessageCreateRequest(BaseModel):
    role: str = "user"
    content: str


class MessageUpdateRequest(BaseModel):
    content: Optional[str] = None


class MessageOut(BaseModel):
    id: str
    chat_id: str
    role: str
    content: str
    owner_email: str
    pinned: bool
    reactions: list[str]
    created_at: datetime


class MessageIdBodyRequest(BaseModel):
    message_id: str


class MessageReactRequest(BaseModel):
    message_id: str
    reaction: str


class MessageReportRequest(BaseModel):
    message_id: str
    reason: str