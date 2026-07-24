"""
Conversation Lifecycle router — CRUD, archive, restore, clone.
Matches the Conversation Lifecycle section of the Conversations & Chat
APIs blueprint (8/8). Only the conversation owner can update/delete/
archive/restore/clone their own conversation.

Literal-path routes (/archive, /restore, /clone) MUST come before the
dynamic /{id} routes below — same ordering rule as fileslifecycle.py.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.conversations import (
    ConversationCreateRequest,
    ConversationUpdateRequest,
    ConversationResponse,
    ConversationIdBodyRequest,
    ConversationCloneRequest,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/conversations", tags=["Conversation Lifecycle"])

# id -> {id, owner_email, title, status, created_at, updated_at}
conversations_db: dict[str, dict] = {}


def _get_conversation_or_404(id: str) -> dict:
    conv = conversations_db.get(id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


def _require_owner(conv: dict, email: str):
    if conv["owner_email"] != email:
        raise HTTPException(status_code=403, detail="Only the conversation owner can perform this action")


@router.get("", response_model=list[ConversationResponse])
def list_conversations(current_user: dict = Depends(get_current_user)):
    return [c for c in conversations_db.values() if c["owner_email"] == current_user["email"]]


@router.post("", response_model=ConversationResponse, status_code=201)
def create_conversation(
    data: ConversationCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    conv_id = str(uuid4())
    now = datetime.now(timezone.utc)
    conversations_db[conv_id] = {
        "id": conv_id,
        "owner_email": current_user["email"],
        "title": data.title,
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }
    return conversations_db[conv_id]


# ─── Literal-path routes MUST come before any /{id} routes below ───

@router.post("/archive", response_model=ConversationResponse)
def archive_conversation(
    data: ConversationIdBodyRequest,
    current_user: dict = Depends(get_current_user),
):
    conv = _get_conversation_or_404(data.conversation_id)
    _require_owner(conv, current_user["email"])
    conv["status"] = "archived"
    conv["updated_at"] = datetime.now(timezone.utc)
    return conv


@router.post("/restore", response_model=ConversationResponse)
def restore_conversation(
    data: ConversationIdBodyRequest,
    current_user: dict = Depends(get_current_user),
):
    conv = _get_conversation_or_404(data.conversation_id)
    _require_owner(conv, current_user["email"])
    conv["status"] = "active"
    conv["updated_at"] = datetime.now(timezone.utc)
    return conv


@router.post("/clone", response_model=ConversationResponse, status_code=201)
def clone_conversation(
    data: ConversationCloneRequest,
    current_user: dict = Depends(get_current_user),
):
    original = _get_conversation_or_404(data.conversation_id)
    _require_owner(original, current_user["email"])

    new_id = str(uuid4())
    now = datetime.now(timezone.utc)
    conversations_db[new_id] = {
        "id": new_id,
        "owner_email": current_user["email"],
        "title": data.new_title or f"{original['title']} (copy)",
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }
    return conversations_db[new_id]


# ─── Dynamic /{id} routes come LAST ───

@router.get("/{id}", response_model=ConversationResponse)
def get_conversation(id: str, current_user: dict = Depends(get_current_user)):
    conv = _get_conversation_or_404(id)
    _require_owner(conv, current_user["email"])
    return conv


@router.patch("/{id}", response_model=ConversationResponse)
def update_conversation(
    id: str,
    data: ConversationUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    conv = _get_conversation_or_404(id)
    _require_owner(conv, current_user["email"])
    if data.title is not None:
        conv["title"] = data.title
    conv["updated_at"] = datetime.now(timezone.utc)
    return conv


@router.delete("/{id}", status_code=204)
def delete_conversation(id: str, current_user: dict = Depends(get_current_user)):
    conv = _get_conversation_or_404(id)
    _require_owner(conv, current_user["email"])
    del conversations_db[id]
    return None