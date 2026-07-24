"""
Pydantic schemas for the Messages domain (Conversations & Chat APIs
blueprint). Messages belong to a conversation owned by conversations.py.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr

MessageRole = Literal["user", "assistant"]


class MessageCreateRequest(BaseModel):
    content: str
    role: MessageRole = "user"


class MessageUpdateRequest(BaseModel):
    content: str


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    sender_email: EmailStr
    role: MessageRole
    content: str
    pinned: bool
    created_at: datetime
    updated_at: datetime


class MessageIdBodyRequest(BaseModel):
    message_id: str