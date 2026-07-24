"""
Pydantic schemas for the History & Search domain (Conversations & Chat
APIs blueprint). Operates over conversations_db/messages_db from
conversations.py/messages.py — no duplicate storage.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr

ConversationStatus = Literal["active", "archived"]


class ConversationSummary(BaseModel):
    id: str
    owner_email: EmailStr
    title: str
    status: ConversationStatus
    created_at: datetime
    updated_at: datetime


class HistorySearchRequest(BaseModel):
    query: str


class HistoryFilterRequest(BaseModel):
    status: ConversationStatus | None = None


class HistoryImportRequest(BaseModel):
    titles: list[str]


class HistoryImportResponse(BaseModel):
    imported_count: int


class HistoryDeleteResponse(BaseModel):
    deleted_conversations: int
    deleted_messages: int


class HistorySummarizeRequest(BaseModel):
    conversation_id: str


class HistorySummarizeResponse(BaseModel):
    conversation_id: str
    summary: str
    message_count: int