"""
Pydantic schemas for the Streaming domain (Conversations & Chat APIs
blueprint). STUBBED: no real LLM streaming pipeline — starting a stream
seeds a few fake token events, but the stream/event records are real
and retrievable.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr

StreamStatus = Literal["active", "stopped", "cancelled"]


class StreamResponse(BaseModel):
    id: str
    conversation_id: str
    owner_email: EmailStr
    status: StreamStatus
    tokens_generated: int
    started_at: datetime
    updated_at: datetime


class StreamIdBodyRequest(BaseModel):
    stream_id: str


class StreamEvent(BaseModel):
    event_type: str
    data: str
    timestamp: datetime


class StreamUsageResponse(BaseModel):
    stream_id: str
    tokens_generated: int
    status: StreamStatus


class StreamHealthResponse(BaseModel):
    status: str
    active_streams: int