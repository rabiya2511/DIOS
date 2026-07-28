"""
Chat Sessions router — CRUD, archive, restore, share, export, import.
Matches the Chat Sessions section of the AI Chat APIs blueprint (10/10).
Only the chat owner can update/delete/archive/restore/share/export their
own chat. Mirrors the structure of projects.py / fileslifecycle.py.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.chat_sessions import (
    ChatCreateRequest,
    ChatUpdateRequest,
    ChatOut,
    ChatIdBodyRequest,
    ChatShareResponse,
    ChatExportOut,
    ChatImportRequest,
)
from app.models.user import chat_sessions_db, chat_shares_db
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/chat", tags=["AI Chat: Chat Sessions"])


def _get_chat_or_404(chat_id: str) -> dict:
    chat = chat_sessions_db.get(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return chat


def _require_owner(chat: dict, email: str):
    if chat["owner_email"] != email:
        raise HTTPException(status_code=403, detail="Only the chat owner can perform this action")


@router.post("", response_model=ChatOut, status_code=201)
def create_chat(
    data: ChatCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    chat_id = str(uuid4())
    now = datetime.now(timezone.utc)
    chat_sessions_db[chat_id] = {
        "id": chat_id,
        "title": data.title,
        "owner_email": current_user["email"],
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }
    return chat_sessions_db[chat_id]


@router.get("", response_model=list[ChatOut])
def list_chats(current_user: dict = Depends(get_current_user)):
    return [c for c in chat_sessions_db.values() if c["owner_email"] == current_user["email"]]


# ─── Literal-path routes MUST come before any /{id} routes below ───

@router.post("/archive", response_model=ChatOut)
def archive_chat(
    data: ChatIdBodyRequest,
    current_user: dict = Depends(get_current_user),
):
    chat = _get_chat_or_404(data.chat_id)
    _require_owner(chat, current_user["email"])
    chat["status"] = "archived"
    chat["updated_at"] = datetime.now(timezone.utc)
    return chat


@router.post("/restore", response_model=ChatOut)
def restore_chat(
    data: ChatIdBodyRequest,
    current_user: dict = Depends(get_current_user),
):
    chat = _get_chat_or_404(data.chat_id)
    _require_owner(chat, current_user["email"])
    chat["status"] = "active"
    chat["updated_at"] = datetime.now(timezone.utc)
    return chat


@router.post("/share", response_model=ChatShareResponse, status_code=201)
def share_chat(
    data: ChatIdBodyRequest,
    current_user: dict = Depends(get_current_user),
):
    chat = _get_chat_or_404(data.chat_id)
    _require_owner(chat, current_user["email"])

    share_token = str(uuid4())
    now = datetime.now(timezone.utc)
    chat_shares_db[share_token] = {
        "chat_id": data.chat_id,
        "shared_by": current_user["email"],
        "created_at": now,
    }
    return ChatShareResponse(
        share_token=share_token,
        chat_id=data.chat_id,
        shared_by=current_user["email"],
        created_at=now,
    )


@router.post("/export", response_model=ChatExportOut)
def export_chat(
    data: ChatIdBodyRequest,
    current_user: dict = Depends(get_current_user),
):
    chat = _get_chat_or_404(data.chat_id)
    _require_owner(chat, current_user["email"])
    return ChatExportOut(
        id=chat["id"],
        title=chat["title"],
        owner_email=chat["owner_email"],
        status=chat["status"],
        exported_at=datetime.now(timezone.utc),
    )


@router.post("/import", response_model=ChatOut, status_code=201)
def import_chat(
    data: ChatImportRequest,
    current_user: dict = Depends(get_current_user),
):
    chat_id = str(uuid4())
    now = datetime.now(timezone.utc)
    chat_sessions_db[chat_id] = {
        "id": chat_id,
        "title": data.title,
        "owner_email": current_user["email"],
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }
    return chat_sessions_db[chat_id]


# ─── Dynamic /{id} routes come LAST ───

@router.get("/{id}", response_model=ChatOut)
def get_chat(id: str, current_user: dict = Depends(get_current_user)):
    chat = _get_chat_or_404(id)
    _require_owner(chat, current_user["email"])
    return chat


@router.patch("/{id}", response_model=ChatOut)
def update_chat(
    id: str,
    data: ChatUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    chat = _get_chat_or_404(id)
    _require_owner(chat, current_user["email"])
    if data.title is not None:
        chat["title"] = data.title
    chat["updated_at"] = datetime.now(timezone.utc)
    return chat


@router.delete("/{id}", status_code=204)
def delete_chat(id: str, current_user: dict = Depends(get_current_user)):
    chat = _get_chat_or_404(id)
    _require_owner(chat, current_user["email"])
    del chat_sessions_db[id]
    return None