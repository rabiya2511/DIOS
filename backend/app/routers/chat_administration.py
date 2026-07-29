"""
Router for the Administration group of the AI Chat APIs blueprint.
  GET  /api/v1/chat/metrics
  GET  /api/v1/chat/usage
  GET  /api/v1/chat/audit
  POST /api/v1/chat/moderate
  POST /api/v1/chat/feedback
  GET  /api/v1/chat/health
  POST /api/v1/chat/cache/clear
  GET  /api/v1/chat/config

Named chat_administration.py (not moderation.py / audit_domain.py /
monitoring_admin.py) to avoid colliding with existing routers of
similar purpose elsewhere in the DIOS app. Uses local in-memory dicts
(same pattern as conversations_db in conversations.py).

All 8 routes are literal paths (no dynamic /{id}), so there's no
ordering concern within this file. As with chat_prompt_context.py and
chat_reasoning_tools.py, include this router in main.py before any
router owning a dynamic /api/v1/chat/{id} route (e.g. chat_sessions)
to avoid cross-router path collisions.

IMPORTANT — /metrics and /usage return placeholder numbers. This
module has no access to the real chat/message stores living in
chat_sessions.py / chat_messages.py (each router owns its own local
dicts, per DIOS convention) — wire these up to real aggregate queries
once there's a shared persistence layer, or pass the other routers'
data in explicitly.

/moderate uses a naive keyword-based check as a placeholder — swap
for a real moderation model/service before relying on this.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.schemas.chat_administration import (
    ChatMetricsResponse,
    ChatUsageResponse,
    ChatAuditLogEntry,
    ChatAuditLogResponse,
    ModerateRequest,
    ModerateResponse,
    FeedbackRequest,
    FeedbackResponse,
    ChatHealthResponse,
    CacheClearRequest,
    CacheClearResponse,
    ChatConfigResponse,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/chat", tags=["Chat Administration"])

_START_TIME = datetime.now(timezone.utc)

# list of {id, actor_email, action, resource_type, resource_id, detail, timestamp}
chat_audit_log_db: list[dict] = []
# id -> {id, chat_id, message_id, flagged, categories, action_taken, created_at}
chat_moderation_log_db: dict[str, dict] = {}
# id -> {id, chat_id, message_id, rating, comment, created_at}
chat_feedback_db: dict[str, dict] = {}

# Naive placeholder wordlist — replace with a real moderation model/service.
_FLAGGED_KEYWORDS = {"hack", "exploit", "malware"}

_CHAT_CONFIG = {
    "features": {
        "streaming": True,
        "multimodal": True,
        "rag": True,
        "agents": False,
    },
    "limits": {
        "max_messages_per_chat": 1000,
        "max_tokens_per_request": 8000,
        "max_context_window": 128000,
    },
}


def _record_audit(actor_email: str, action: str, resource_type: str,
                   resource_id: Optional[str] = None, detail: Optional[str] = None) -> None:
    chat_audit_log_db.append({
        "id": str(uuid.uuid4()),
        "actor_email": actor_email,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "detail": detail,
        "timestamp": datetime.now(timezone.utc),
    })


# ---------------------------------------------------------------------------
# GET /api/v1/chat/metrics
# ---------------------------------------------------------------------------
@router.get("/metrics", response_model=ChatMetricsResponse)
def get_chat_metrics(
    current_user: dict = Depends(get_current_user),
):
    """Aggregate chat metrics. Placeholder values — see module docstring."""
    return ChatMetricsResponse(
        total_chats=0,
        total_messages=0,
        active_chats_last_24h=0,
        avg_response_time_ms=0.0,
        generated_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# GET /api/v1/chat/usage
# ---------------------------------------------------------------------------
@router.get("/usage", response_model=ChatUsageResponse)
def get_chat_usage(
    chat_id: Optional[str] = Query(None),
    period_start: Optional[datetime] = Query(None),
    period_end: Optional[datetime] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    """Token/request usage stats. Placeholder values — see module docstring."""
    return ChatUsageResponse(
        chat_id=chat_id,
        total_tokens=0,
        total_requests=0,
        period_start=period_start,
        period_end=period_end,
        generated_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# GET /api/v1/chat/audit
# ---------------------------------------------------------------------------
@router.get("/audit", response_model=ChatAuditLogResponse)
def get_chat_audit_log(
    action: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    """Retrieve the audit log of admin actions taken through this module."""
    entries = chat_audit_log_db
    if action:
        entries = [e for e in entries if e["action"] == action]

    entries_sorted = sorted(entries, key=lambda e: e["timestamp"], reverse=True)
    total = len(entries_sorted)
    page = entries_sorted[offset: offset + limit]
    return ChatAuditLogResponse(total=total, items=page)


# ---------------------------------------------------------------------------
# POST /api/v1/chat/moderate
# ---------------------------------------------------------------------------
@router.post("/moderate", response_model=ModerateResponse)
def moderate_content(
    payload: ModerateRequest,
    current_user: dict = Depends(get_current_user),
):
    """Run (naive, placeholder) moderation over chat content."""
    content_lower = payload.content.lower()
    matched = [kw for kw in _FLAGGED_KEYWORDS if kw in content_lower]
    flagged = len(matched) > 0
    action_taken = "blocked" if flagged else "allowed"

    moderation_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    chat_moderation_log_db[moderation_id] = {
        "id": moderation_id,
        "chat_id": payload.chat_id,
        "message_id": payload.message_id,
        "flagged": flagged,
        "categories": matched,
        "action_taken": action_taken,
        "created_at": now,
    }

    _record_audit(
        current_user.get("email", "unknown"), "moderate", "chat_message",
        resource_id=payload.message_id or payload.chat_id,
        detail=f"flagged={flagged}",
    )

    return ModerateResponse(
        id=moderation_id, chat_id=payload.chat_id, message_id=payload.message_id,
        flagged=flagged, categories=matched, action_taken=action_taken, created_at=now,
    )


# ---------------------------------------------------------------------------
# POST /api/v1/chat/feedback
# ---------------------------------------------------------------------------
@router.post("/feedback", response_model=FeedbackResponse)
def submit_feedback(
    payload: FeedbackRequest,
    current_user: dict = Depends(get_current_user),
):
    """Submit feedback (rating + optional comment) for a chat or message."""
    feedback_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    chat_feedback_db[feedback_id] = {
        "id": feedback_id,
        "chat_id": payload.chat_id,
        "message_id": payload.message_id,
        "rating": payload.rating,
        "comment": payload.comment,
        "created_at": now,
    }

    _record_audit(
        current_user.get("email", "unknown"), "feedback_submitted", "chat_message",
        resource_id=payload.message_id or payload.chat_id,
    )

    return FeedbackResponse(
        id=feedback_id, chat_id=payload.chat_id, message_id=payload.message_id,
        rating=payload.rating, comment=payload.comment, created_at=now,
    )


# ---------------------------------------------------------------------------
# GET /api/v1/chat/health
# ---------------------------------------------------------------------------
@router.get("/health", response_model=ChatHealthResponse)
def chat_health(
    current_user: dict = Depends(get_current_user),
):
    """Health check for the chat subsystem."""
    now = datetime.now(timezone.utc)
    uptime = (now - _START_TIME).total_seconds()
    return ChatHealthResponse(status="ok", uptime_seconds=uptime, checked_at=now)


# ---------------------------------------------------------------------------
# POST /api/v1/chat/cache/clear
# ---------------------------------------------------------------------------
@router.post("/cache/clear", response_model=CacheClearResponse)
def clear_chat_cache(
    payload: CacheClearRequest,
    current_user: dict = Depends(get_current_user),
):
    """Clear chat-related caches. scope='chat' requires chat_id."""
    if payload.scope == "chat" and not payload.chat_id:
        raise HTTPException(status_code=400, detail="chat_id is required when scope='chat'")

    now = datetime.now(timezone.utc)
    _record_audit(
        current_user.get("email", "unknown"), "cache_cleared", "chat_cache",
        resource_id=payload.chat_id, detail=f"scope={payload.scope}",
    )

    return CacheClearResponse(
        scope=payload.scope, chat_id=payload.chat_id, cleared=True, cleared_at=now,
    )


# ---------------------------------------------------------------------------
# GET /api/v1/chat/config
# ---------------------------------------------------------------------------
@router.get("/config", response_model=ChatConfigResponse)
def get_chat_config(
    current_user: dict = Depends(get_current_user),
):
    """Retrieve current chat feature flags and limits."""
    return ChatConfigResponse(
        features=_CHAT_CONFIG["features"],
        limits=_CHAT_CONFIG["limits"],
        updated_at=_START_TIME,
    )