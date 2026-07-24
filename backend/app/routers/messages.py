"""
Messages router — list/create (nested under conversations), edit,
delete, retry, regenerate, pin/unpin. Matches the Messages section of
the Conversations & Chat APIs blueprint (8/8).

Router prefix is "/api/v1" (not "/api/v1/messages") since this domain
mixes two path shapes: /conversations/{id}/messages (3 segments, won't
collide with conversations.py's 2-segment /conversations/{id}) and flat
/messages/... routes. Within THIS router, literal paths (/messages/retry,
/messages/regenerate, /messages/pin) MUST come before /messages/{id.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.messages import (
    MessageCreateRequest,
    MessageUpdateRequest,
    MessageResponse,
    MessageIdBodyRequest,
)
from app.routers.conversations import conversations_db, _get_conversation_or_404, _require_owner
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1", tags=["Messages"])

# id -> {id, conversation_id, sender_email, role, content, pinned, created_at, updated_at}
messages_db: dict[str, dict] = {}


def _get_message_or_404(id: str) -> dict:
    msg = messages_db.get(id)
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    return msg


def _require_message_owner(msg: dict, email: str):
    if msg["sender_email"] != email:
        raise HTTPException(status_code=403, detail="Only the message sender can perform this action")


@router.get("/conversations/{id}/messages", response_model=list[MessageResponse])
def list_messages(id: str, current_user: dict = Depends(get_current_user)):
    conv = _get_conversation_or_404(id)
    _require_owner(conv, current_user["email"])
    return [m for m in messages_db.values() if m["conversation_id"] == id]


@router.post("/conversations/{id}/messages", response_model=MessageResponse, status_code=201)
def create_message(
    id: str,
    data: MessageCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    conv = _get_conversation_or_404(id)
    _require_owner(conv, current_user["email"])

    message_id = str(uuid4())
    now = datetime.now(timezone.utc)
    messages_db[message_id] = {
        "id": message_id,
        "conversation_id": id,
        "sender_email": current_user["email"],
        "role": data.role,
        "content": data.content,
        "pinned": False,
        "created_at": now,
        "updated_at": now,
    }
    return messages_db[message_id]


# ─── Literal-path routes MUST come before /messages/{id} below ───

@router.post("/messages/retry", response_model=MessageResponse, status_code=201)
def retry_message(
    data: MessageIdBodyRequest,
    current_user: dict = Depends(get_current_user),
):
    original = _get_message_or_404(data.message_id)
    _require_message_owner(original, current_user["email"])

    new_id = str(uuid4())
    now = datetime.now(timezone.utc)
    messages_db[new_id] = {
        "id": new_id,
        "conversation_id": original["conversation_id"],
        "sender_email": current_user["email"],
        "role": "assistant",
        "content": f"[Retried response for message {original['id']}]",
        "pinned": False,
        "created_at": now,
        "updated_at": now,
    }
    return messages_db[new_id]


@router.post("/messages/regenerate", response_model=MessageResponse, status_code=201)
def regenerate_message(
    data: MessageIdBodyRequest,
    current_user: dict = Depends(get_current_user),
):
    original = _get_message_or_404(data.message_id)
    _require_message_owner(original, current_user["email"])

    new_id = str(uuid4())
    now = datetime.now(timezone.utc)
    messages_db[new_id] = {
        "id": new_id,
        "conversation_id": original["conversation_id"],
        "sender_email": current_user["email"],
        "role": "assistant",
        "content": f"[Regenerated response replacing message {original['id']}]",
        "pinned": False,
        "created_at": now,
        "updated_at": now,
    }
    return messages_db[new_id]


@router.post("/messages/pin", response_model=MessageResponse)
def pin_message(
    data: MessageIdBodyRequest,
    current_user: dict = Depends(get_current_user),
):
    msg = _get_message_or_404(data.message_id)
    _require_message_owner(msg, current_user["email"])
    msg["pinned"] = True
    msg["updated_at"] = datetime.now(timezone.utc)
    return msg


@router.delete("/messages/pin", response_model=MessageResponse)
def unpin_message(
    data: MessageIdBodyRequest,
    current_user: dict = Depends(get_current_user),
):
    msg = _get_message_or_404(data.message_id)
    _require_message_owner(msg, current_user["email"])
    msg["pinned"] = False
    msg["updated_at"] = datetime.now(timezone.utc)
    return msg


# ─── Dynamic /messages/{id} routes come LAST ───

@router.patch("/messages/{id}", response_model=MessageResponse)
def update_message(
    id: str,
    data: MessageUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    msg = _get_message_or_404(id)
    _require_message_owner(msg, current_user["email"])
    msg["content"] = data.content
    msg["updated_at"] = datetime.now(timezone.utc)
    return msg


@router.delete("/messages/{id}", status_code=204)
def delete_message(id: str, current_user: dict = Depends(get_current_user)):
    msg = _get_message_or_404(id)
    _require_message_owner(msg, current_user["email"])
    del messages_db[id]
    return None