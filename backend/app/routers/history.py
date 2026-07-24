"""
History & Search router — list, search, filter, export, import, delete,
summarize, recent. Matches the History & Search section of the
Conversations & Chat APIs blueprint (8/8).

Operates directly over conversations_db (from conversations.py) and
messages_db (from messages.py) — no duplicate storage. No dynamic
/{id} routes in this domain, so there's no route-ordering conflict
with conversations.py or messages.py.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, Query

from app.schemas.history import (
    ConversationSummary,
    HistorySearchRequest,
    HistoryFilterRequest,
    HistoryImportRequest,
    HistoryImportResponse,
    HistoryDeleteResponse,
    HistorySummarizeRequest,
    HistorySummarizeResponse,
)
from app.core.security import get_current_user
from app.routers.conversations import conversations_db, _get_conversation_or_404, _require_owner
from app.routers.messages import messages_db

router = APIRouter(prefix="/api/v1/history", tags=["History & Search"])


def _owned_conversations(email: str) -> list[dict]:
    return [c for c in conversations_db.values() if c["owner_email"] == email]


@router.get("", response_model=list[ConversationSummary])
def get_history(current_user: dict = Depends(get_current_user)):
    return _owned_conversations(current_user["email"])


@router.post("/search", response_model=list[ConversationSummary])
def search_history(
    data: HistorySearchRequest,
    current_user: dict = Depends(get_current_user),
):
    query = data.query.lower()
    return [
        c for c in _owned_conversations(current_user["email"])
        if query in c["title"].lower()
    ]


@router.post("/filter", response_model=list[ConversationSummary])
def filter_history(
    data: HistoryFilterRequest,
    current_user: dict = Depends(get_current_user),
):
    results = _owned_conversations(current_user["email"])
    if data.status:
        results = [c for c in results if c["status"] == data.status]
    return results


@router.post("/export", response_model=list[ConversationSummary])
def export_history(current_user: dict = Depends(get_current_user)):
    """Export all of the current user's conversations as JSON."""
    return _owned_conversations(current_user["email"])


@router.post("/import", response_model=HistoryImportResponse, status_code=201)
def import_history(
    data: HistoryImportRequest,
    current_user: dict = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)
    for title in data.titles:
        conv_id = str(uuid4())
        conversations_db[conv_id] = {
            "id": conv_id,
            "owner_email": current_user["email"],
            "title": title,
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }
    return HistoryImportResponse(imported_count=len(data.titles))


@router.delete("", response_model=HistoryDeleteResponse)
def delete_history(current_user: dict = Depends(get_current_user)):
    """Delete all of the current user's conversations and their messages."""
    owned_ids = {c["id"] for c in _owned_conversations(current_user["email"])}

    deleted_messages = 0
    for msg_id in [mid for mid, m in messages_db.items() if m["conversation_id"] in owned_ids]:
        del messages_db[msg_id]
        deleted_messages += 1

    deleted_conversations = 0
    for conv_id in owned_ids:
        del conversations_db[conv_id]
        deleted_conversations += 1

    return HistoryDeleteResponse(
        deleted_conversations=deleted_conversations,
        deleted_messages=deleted_messages,
    )


@router.post("/summarize", response_model=HistorySummarizeResponse)
def summarize_history(
    data: HistorySummarizeRequest,
    current_user: dict = Depends(get_current_user),
):
    conv = _get_conversation_or_404(data.conversation_id)
    _require_owner(conv, current_user["email"])

    conv_messages = [m for m in messages_db.values() if m["conversation_id"] == data.conversation_id]
    summary = (
        f"Conversation '{conv['title']}' has {len(conv_messages)} message(s). "
        "This is a placeholder summary — real summarization requires an LLM call."
    )
    return HistorySummarizeResponse(
        conversation_id=data.conversation_id,
        summary=summary,
        message_count=len(conv_messages),
    )


@router.get("/recent", response_model=list[ConversationSummary])
def recent_history(
    limit: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    results = _owned_conversations(current_user["email"])
    results.sort(key=lambda c: c["updated_at"], reverse=True)
    return results[:limit]