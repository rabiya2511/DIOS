"""
Pydantic schemas for the Conversation Lifecycle domain (Conversations &
Chat APIs blueprint).
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr

ConversationStatus = Literal["active", "archived"]


class ConversationCreateRequest(BaseModel):
    title: str


class ConversationUpdateRequest(BaseModel):
    title: str | None = None


class ConversationResponse(BaseModel):
    id: str
    owner_email: EmailStr
    title: str
    status: ConversationStatus
    created_at: datetime
    updated_at: datetime


class ConversationIdBodyRequest(BaseModel):
    conversation_id: str


class ConversationCloneRequest(BaseModel):
    conversation_id: str
    new_title: str | None = None