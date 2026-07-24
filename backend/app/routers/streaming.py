"""
Streaming router — start, stop, status, reconnect, events, usage,
cancel, health. Matches the Streaming section of the Conversations &
Chat APIs blueprint (8/8). STUBBED: no real LLM streaming pipeline.

POST /conversations/{id}/stream is 3 segments — won't collide with
conversations.py's 2-segment GET/PATCH/DELETE /conversations/{id}.
Every /stream/... path here is a fixed literal string (no dynamic
segments), so there's no internal ordering concern in this router.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.streaming import (
    StreamResponse,
    StreamIdBodyRequest,
    StreamEvent,
    StreamUsageResponse,
    StreamHealthResponse,
)
from app.routers.conversations import _get_conversation_or_404, _require_owner
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1", tags=["Streaming"])

# id -> {id, conversation_id, owner_email, status, tokens_generated, started_at, updated_at}
streams_db: dict[str, dict] = {}

# stream_id -> list of {event_type, data, timestamp}
stream_events_db: dict[str, list] = {}


def _get_owned_stream(stream_id: str, email: str) -> dict:
    stream = streams_db.get(stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    if stream["owner_email"] != email:
        raise HTTPException(status_code=403, detail="Only the stream owner can perform this action")
    return stream


@router.post("/conversations/{id}/stream", response_model=StreamResponse, status_code=201)
def start_stream(id: str, current_user: dict = Depends(get_current_user)):
    conv = _get_conversation_or_404(id)
    _require_owner(conv, current_user["email"])

    stream_id = str(uuid4())
    now = datetime.now(timezone.utc)
    streams_db[stream_id] = {
        "id": stream_id,
        "conversation_id": id,
        "owner_email": current_user["email"],
        "status": "active",
        "tokens_generated": 24,  # STUB: simulated token count from seeded events
        "started_at": now,
        "updated_at": now,
    }
    stream_events_db[stream_id] = [
        {"event_type": "token", "data": "Sure,", "timestamp": now},
        {"event_type": "token", "data": " here's", "timestamp": now},
        {"event_type": "token", "data": " an answer.", "timestamp": now},
    ]
    return streams_db[stream_id]


@router.post("/stream/stop", response_model=StreamResponse)
def stop_stream(data: StreamIdBodyRequest, current_user: dict = Depends(get_current_user)):
    stream = _get_owned_stream(data.stream_id, current_user["email"])
    if stream["status"] == "cancelled":
        raise HTTPException(status_code=400, detail="Cannot stop a cancelled stream")
    stream["status"] = "stopped"
    stream["updated_at"] = datetime.now(timezone.utc)
    return stream


@router.get("/stream/status", response_model=StreamResponse)
def get_stream_status(stream_id: str, current_user: dict = Depends(get_current_user)):
    return _get_owned_stream(stream_id, current_user["email"])


@router.post("/stream/reconnect", response_model=StreamResponse)
def reconnect_stream(data: StreamIdBodyRequest, current_user: dict = Depends(get_current_user)):
    stream = _get_owned_stream(data.stream_id, current_user["email"])
    if stream["status"] == "cancelled":
        raise HTTPException(status_code=400, detail="Cannot reconnect a cancelled stream")
    stream["status"] = "active"
    stream["updated_at"] = datetime.now(timezone.utc)
    return stream


@router.get("/stream/events", response_model=list[StreamEvent])
def get_stream_events(stream_id: str, current_user: dict = Depends(get_current_user)):
    _get_owned_stream(stream_id, current_user["email"])
    return stream_events_db.get(stream_id, [])


@router.get("/stream/usage", response_model=StreamUsageResponse)
def get_stream_usage(stream_id: str, current_user: dict = Depends(get_current_user)):
    stream = _get_owned_stream(stream_id, current_user["email"])
    return StreamUsageResponse(
        stream_id=stream["id"],
        tokens_generated=stream["tokens_generated"],
        status=stream["status"],
    )


@router.post("/stream/cancel", response_model=StreamResponse)
def cancel_stream(data: StreamIdBodyRequest, current_user: dict = Depends(get_current_user)):
    stream = _get_owned_stream(data.stream_id, current_user["email"])
    stream["status"] = "cancelled"
    stream["updated_at"] = datetime.now(timezone.utc)
    return stream


@router.get("/stream/health", response_model=StreamHealthResponse)
def get_stream_health():
    active_count = sum(1 for s in streams_db.values() if s["status"] == "active")
    return StreamHealthResponse(status="ok", active_streams=active_count)