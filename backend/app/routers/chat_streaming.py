"""
AI Chat Streaming router — start, cancel, status, resume, events,
token-usage, health, reconnect. Matches the Streaming section of the
AI Chat APIs blueprint (8/8). STUBBED: no real model streaming.

Every path here is a fixed literal string under /chat/stream/... (no
dynamic {id} segments), so there's no internal ordering concern.
Entirely separate from the earlier Conversations & Chat Streaming
domain (/stream/... paths, different router/storage).
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.chat_streaming import (
    ChatStreamStartRequest,
    ChatStreamResponse,
    ChatStreamIdBodyRequest,
    ChatStreamEvent,
    ChatStreamTokenUsageResponse,
    ChatStreamHealthResponse,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/chat", tags=["AI Chat Streaming"])

# id -> {id, owner_email, status, tokens_used, created_at, updated_at}
chat_streams_db: dict[str, dict] = {}

# stream_id -> list of {event_type, data, timestamp}
chat_stream_events_db: dict[str, list] = {}


def _get_owned_stream(stream_id: str, email: str) -> dict:
    stream = chat_streams_db.get(stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Chat stream not found")
    if stream["owner_email"] != email:
        raise HTTPException(status_code=403, detail="Only the stream owner can perform this action")
    return stream


@router.post("/stream", response_model=ChatStreamResponse, status_code=201)
def start_stream(data: ChatStreamStartRequest, current_user: dict = Depends(get_current_user)):
    stream_id = str(uuid4())
    now = datetime.now(timezone.utc)
    chat_streams_db[stream_id] = {
        "id": stream_id,
        "owner_email": current_user["email"],
        "status": "streaming",
        "tokens_used": 18,  # STUB: simulated
        "created_at": now,
        "updated_at": now,
    }
    chat_stream_events_db[stream_id] = [
        {"event_type": "token", "data": "Here's", "timestamp": now},
        {"event_type": "token", "data": " what I found:", "timestamp": now},
    ]
    return chat_streams_db[stream_id]


@router.post("/stream/cancel", response_model=ChatStreamResponse)
def cancel_stream(data: ChatStreamIdBodyRequest, current_user: dict = Depends(get_current_user)):
    stream = _get_owned_stream(data.stream_id, current_user["email"])
    stream["status"] = "cancelled"
    stream["updated_at"] = datetime.now(timezone.utc)
    return stream


@router.get("/stream/status", response_model=ChatStreamResponse)
def get_stream_status(stream_id: str, current_user: dict = Depends(get_current_user)):
    return _get_owned_stream(stream_id, current_user["email"])


@router.post("/stream/resume", response_model=ChatStreamResponse)
def resume_stream(data: ChatStreamIdBodyRequest, current_user: dict = Depends(get_current_user)):
    stream = _get_owned_stream(data.stream_id, current_user["email"])
    if stream["status"] == "cancelled":
        raise HTTPException(status_code=400, detail="Cannot resume a cancelled stream")
    stream["status"] = "streaming"
    stream["updated_at"] = datetime.now(timezone.utc)
    return stream


@router.post("/stream/events", response_model=list[ChatStreamEvent])
def get_stream_events(data: ChatStreamIdBodyRequest, current_user: dict = Depends(get_current_user)):
    _get_owned_stream(data.stream_id, current_user["email"])
    return chat_stream_events_db.get(data.stream_id, [])


@router.post("/stream/token-usage", response_model=ChatStreamTokenUsageResponse)
def get_token_usage(data: ChatStreamIdBodyRequest, current_user: dict = Depends(get_current_user)):
    stream = _get_owned_stream(data.stream_id, current_user["email"])
    return ChatStreamTokenUsageResponse(stream_id=stream["id"], tokens_used=stream["tokens_used"])


@router.get("/stream/health", response_model=ChatStreamHealthResponse)
def get_stream_health():
    active_count = sum(1 for s in chat_streams_db.values() if s["status"] == "streaming")
    return ChatStreamHealthResponse(status="ok", active_streams=active_count)


@router.post("/stream/reconnect", response_model=ChatStreamResponse)
def reconnect_stream(data: ChatStreamIdBodyRequest, current_user: dict = Depends(get_current_user)):
    stream = _get_owned_stream(data.stream_id, current_user["email"])
    if stream["status"] == "cancelled":
        raise HTTPException(status_code=400, detail="Cannot reconnect a cancelled stream")
    stream["status"] = "streaming"
    stream["updated_at"] = datetime.now(timezone.utc)
    return stream