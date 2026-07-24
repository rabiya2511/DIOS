"""
Sharing & Collaboration router — share, comment, tag, favorite.
Matches the Sharing & Collaboration section of the Conversations & Chat
APIs blueprint (8/8).

IMPORTANT: Shares the /api/v1/conversations prefix with conversations.py
(Conversation Lifecycle). This router MUST be included in main.py
BEFORE conversations.router — several routes here (GET /comments,
DELETE /share, DELETE /tag, DELETE /favorite) are single-segment paths
that would otherwise collide with conversations.py's dynamic
GET/PATCH/DELETE /conversations/{id} routes.

Access rule: the conversation owner or anyone it's been shared with
can comment/view comments; only the owner can share/unshare, tag/untag,
or manage the share list. Favoriting is per-user and doesn't require
ownership (just visibility, i.e. owner or shared-with).
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query

from app.schemas.sharing import (
    ConversationShareRequest,
    ConversationShareResponse,
    CommentCreateRequest,
    CommentResponse,
    ConversationTagRequest,
    ConversationFavoriteRequest,
)
from app.core.security import get_current_user
from app.routers.conversations import conversations_db, _get_conversation_or_404, _require_owner

router = APIRouter(prefix="/api/v1/conversations", tags=["Sharing & Collaboration"])

# conversation_id -> set of emails the conversation is shared with
shares_db: dict[str, set] = {}

# comment_id -> {id, conversation_id, author_email, content, created_at}
comments_db: dict[str, dict] = {}

# conversation_id -> set of tags
tags_db: dict[str, set] = {}

# email -> set of favorited conversation_ids
favorites_db: dict[str, set] = {}


def _require_visibility(conv: dict, email: str):
    """Owner or someone the conversation is shared with can view/comment."""
    if conv["owner_email"] == email:
        return
    if email in shares_db.get(conv["id"], set()):
        return
    raise HTTPException(status_code=403, detail="You don't have access to this conversation")


@router.post("/share", response_model=ConversationShareResponse, status_code=201)
def share_conversation(
    data: ConversationShareRequest,
    current_user: dict = Depends(get_current_user),
):
    conv = _get_conversation_or_404(data.conversation_id)
    _require_owner(conv, current_user["email"])
    shares_db.setdefault(data.conversation_id, set()).add(data.email)
    return ConversationShareResponse(
        conversation_id=data.conversation_id,
        shared_with_email=data.email,
        shared_at=datetime.now(timezone.utc),
    )


@router.delete("/share", status_code=204)
def unshare_conversation(
    data: ConversationShareRequest,
    current_user: dict = Depends(get_current_user),
):
    conv = _get_conversation_or_404(data.conversation_id)
    _require_owner(conv, current_user["email"])
    shares_db.setdefault(data.conversation_id, set()).discard(data.email)
    return None


@router.post("/comment", response_model=CommentResponse, status_code=201)
def add_comment(
    data: CommentCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    conv = _get_conversation_or_404(data.conversation_id)
    _require_visibility(conv, current_user["email"])

    comment_id = str(uuid4())
    now = datetime.now(timezone.utc)
    comments_db[comment_id] = {
        "id": comment_id,
        "conversation_id": data.conversation_id,
        "author_email": current_user["email"],
        "content": data.content,
        "created_at": now,
    }
    return comments_db[comment_id]


@router.get("/comments", response_model=list[CommentResponse])
def get_comments(
    conversation_id: str = Query(...),
    current_user: dict = Depends(get_current_user),
):
    conv = _get_conversation_or_404(conversation_id)
    _require_visibility(conv, current_user["email"])
    return [c for c in comments_db.values() if c["conversation_id"] == conversation_id]


@router.post("/tag", status_code=201)
def add_tag(
    data: ConversationTagRequest,
    current_user: dict = Depends(get_current_user),
):
    conv = _get_conversation_or_404(data.conversation_id)
    _require_owner(conv, current_user["email"])
    tags_db.setdefault(data.conversation_id, set()).add(data.tag)
    return {"conversation_id": data.conversation_id, "tags": sorted(tags_db[data.conversation_id])}


@router.delete("/tag")
def remove_tag(
    data: ConversationTagRequest,
    current_user: dict = Depends(get_current_user),
):
    conv = _get_conversation_or_404(data.conversation_id)
    _require_owner(conv, current_user["email"])
    tags_db.setdefault(data.conversation_id, set()).discard(data.tag)
    return {"conversation_id": data.conversation_id, "tags": sorted(tags_db[data.conversation_id])}


@router.post("/favorite", status_code=201)
def favorite_conversation(
    data: ConversationFavoriteRequest,
    current_user: dict = Depends(get_current_user),
):
    conv = _get_conversation_or_404(data.conversation_id)
    _require_visibility(conv, current_user["email"])
    favorites_db.setdefault(current_user["email"], set()).add(data.conversation_id)
    return {"conversation_id": data.conversation_id, "favorited": True}


@router.delete("/favorite")
def unfavorite_conversation(
    data: ConversationFavoriteRequest,
    current_user: dict = Depends(get_current_user),
):
    conv = _get_conversation_or_404(data.conversation_id)
    _require_visibility(conv, current_user["email"])
    favorites_db.setdefault(current_user["email"], set()).discard(data.conversation_id)
    return {"conversation_id": data.conversation_id, "favorited": False}