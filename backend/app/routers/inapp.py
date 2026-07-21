"""
In-App router — send, feed, bulk mark-read, delete.
Matches the In-App section of the Notifications APIs blueprint (4/4).
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.inapp import (
    InAppSendRequest,
    InAppMessageResponse,
    InAppMarkReadRequest,
    InAppMarkReadResponse,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/inapp", tags=["In-App"])

# id -> {id, recipient_email, title, body, read, created_at}
inapp_messages_db: dict[str, dict] = {}


@router.post("/send", response_model=InAppMessageResponse, status_code=201)
def send_inapp_message(
    data: InAppSendRequest,
    current_user: dict = Depends(get_current_user),
):
    message_id = str(uuid4())
    now = datetime.now(timezone.utc)
    inapp_messages_db[message_id] = {
        "id": message_id,
        "recipient_email": data.recipient_email,
        "title": data.title,
        "body": data.body,
        "read": False,
        "created_at": now,
    }
    return inapp_messages_db[message_id]


@router.get("/feed", response_model=list[InAppMessageResponse])
def get_feed(current_user: dict = Depends(get_current_user)):
    messages = [
        m for m in inapp_messages_db.values() if m["recipient_email"] == current_user["email"]
    ]
    return sorted(messages, key=lambda m: m["created_at"], reverse=True)


@router.patch("/read", response_model=InAppMarkReadResponse)
def mark_read(
    data: InAppMarkReadRequest,
    current_user: dict = Depends(get_current_user),
):
    marked = 0
    not_found = 0
    for message_id in data.ids:
        m = inapp_messages_db.get(message_id)
        if m and m["recipient_email"] == current_user["email"]:
            m["read"] = True
            marked += 1
        else:
            not_found += 1
    return InAppMarkReadResponse(marked_read=marked, not_found=not_found)


@router.delete("/{id}", status_code=204)
def delete_inapp_message(id: str, current_user: dict = Depends(get_current_user)):
    m = inapp_messages_db.get(id)
    if not m or m["recipient_email"] != current_user["email"]:
        raise HTTPException(status_code=404, detail="Message not found")
    del inapp_messages_db[id]
    return None