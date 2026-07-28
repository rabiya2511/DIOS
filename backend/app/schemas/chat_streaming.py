"""
Pydantic schemas for the AI Chat Streaming domain (AI Chat APIs
blueprint). STUBBED: no real model streaming — stream/event records
are real and retrievable, content is simulated. Distinct from the
earlier Conversations & Chat Streaming domain (/stream/... vs
/chat/stream/...) — separate storage, no shared state.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr

ChatStreamStatus = Literal["streaming", "paused", "cancelled"]


class ChatStreamStartRequest(BaseModel):
    prompt: str


class ChatStreamResponse(BaseModel):
    id: str
    owner_email: EmailStr
    status: ChatStreamStatus
    tokens_used: int
    created_at: datetime
    updated_at: datetime


class ChatStreamIdBodyRequest(BaseModel):
    stream_id: str


class ChatStreamEvent(BaseModel):
    event_type: str
    data: str
    timestamp: datetime


class ChatStreamTokenUsageResponse(BaseModel):
    stream_id: str
    tokens_used: int


class ChatStreamHealthResponse(BaseModel):
    status: str
    active_streams: int