"""
Messaging router — send/list messages, update/delete, retry, regenerate,
pin/unpin, react, report.
Matches the Messaging section of the AI Chat APIs blueprint (10/10).

IMPORTANT: The flat routes here use /chat-messages/... instead of
/messages/... because /messages/{id}, /messages/retry, /messages/regenerate,
and /messages/pin already exist in messages.py (Conversations & Chat
blueprint's Messages domain) with the exact same paths+methods. Reusing
/messages/... here would silently collide — whichever router is included
first in main.py would win, making the other's route unreachable.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.chat_messages import (
    MessageCreateRequest,
    MessageUpdateRequest,
    MessageOut,
    MessageIdBodyRequest,
    MessageReactRequest,
    MessageReportRequest,
)
from app.models.user import chat_messages_db
from app.routers.chat_sessions import chat_sessions_db, _get_chat_or_404, _require_owner
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1", tags=["AI Chat: Messaging"])


def _get_message_or_404(message_id: str) -> dict:
    msg = chat_messages_db.get(message_id)
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    return msg


def _require_message_owner(msg: dict, email: str):
    if msg["owner_email"] != email:
        raise HTTPException(status_code=403, detail="Only the message owner can perform this action")


@router.post("/chat/{id}/messages", response_model=MessageOut, status_code=201)
def send_message(
    id: str,
    data: MessageCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    chat = _get_chat_or_404(id)
    _require_owner(chat, current_user["email"])

    message_id = str(uuid4())
    message = {
        "id": message_id,
        "chat_id": id,
        "role": data.role,
        "content": data.content,
        "owner_email": current_user["email"],
        "pinned": False,
        "reactions": [],
        "created_at": datetime.now(timezone.utc),
    }
    chat_messages_db[message_id] = message
    return message


@router.get("/chat/{id}/messages", response_model=list[MessageOut])
def list_messages(id: str, current_user: dict = Depends(get_current_user)):
    chat = _get_chat_or_404(id)
    _require_owner(chat, current_user["email"])
    return [m for m in chat_messages_db.values() if m["chat_id"] == id]


# ─── Literal-path routes before /chat-messages/{id} below ───

@router.post("/chat-messages/retry", response_model=MessageOut, status_code=201)
def retry_message(
    data: MessageIdBodyRequest,
    current_user: dict = Depends(get_current_user),
):
    original = _get_message_or_404(data.message_id)
    _require_message_owner(original, current_user["email"])

    new_id = str(uuid4())
    message = {
        "id": new_id,
        "chat_id": original["chat_id"],
        "role": original["role"],
        "content": original["content"],
        "owner_email": current_user["email"],
        "pinned": False,
        "reactions": [],
        "created_at": datetime.now(timezone.utc),
    }
    chat_messages_db[new_id] = message
    return message


@router.post("/chat-messages/regenerate", response_model=MessageOut, status_code=201)
def regenerate_message(
    data: MessageIdBodyRequest,
    current_user: dict = Depends(get_current_user),
):
    original = _get_message_or_404(data.message_id)
    _require_message_owner(original, current_user["email"])

    new_id = str(uuid4())
    # STUB: real version would call the model again; here we simulate a new response.
    message = {
        "id": new_id,
        "chat_id": original["chat_id"],
        "role": "assistant",
        "content": f"[regenerated response to: {original['content'][:50]}]",
        "owner_email": current_user["email"],
        "pinned": False,
        "reactions": [],
        "created_at": datetime.now(timezone.utc),
    }
    chat_messages_db[new_id] = message
    return message


@router.post("/chat-messages/pin", response_model=MessageOut)
def pin_message(
    data: MessageIdBodyRequest,
    current_user: dict = Depends(get_current_user),
):
    msg = _get_message_or_404(data.message_id)
    _require_message_owner(msg, current_user["email"])
    msg["pinned"] = True
    return msg


@router.delete("/chat-messages/pin", response_model=MessageOut)
def unpin_message(
    data: MessageIdBodyRequest,
    current_user: dict = Depends(get_current_user),
):
    msg = _get_message_or_404(data.message_id)
    _require_message_owner(msg, current_user["email"])
    msg["pinned"] = False
    return msg


@router.post("/chat-messages/react", response_model=MessageOut)
def react_to_message(
    data: MessageReactRequest,
    current_user: dict = Depends(get_current_user),
):
    msg = _get_message_or_404(data.message_id)
    msg["reactions"].append(data.reaction)
    return msg


@router.post("/chat-messages/report", status_code=201)
def report_message(
    data: MessageReportRequest,
    current_user: dict = Depends(get_current_user),
):
    _get_message_or_404(data.message_id)  # confirm it exists
    return {
        "message_id": data.message_id,
        "reported_by": current_user["email"],
        "reason": data.reason,
        "status": "received",
    }


# ─── Dynamic /chat-messages/{id} routes come LAST ───

@router.patch("/chat-messages/{id}", response_model=MessageOut)
def update_message(
    id: str,
    data: MessageUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    msg = _get_message_or_404(id)
    _require_message_owner(msg, current_user["email"])
    if data.content is not None:
        msg["content"] = data.content
    return msg


@router.delete("/chat-messages/{id}", status_code=204)
def delete_message(id: str, current_user: dict = Depends(get_current_user)):
    msg = _get_message_or_404(id)
    _require_message_owner(msg, current_user["email"])
    del chat_messages_db[id]
    return None