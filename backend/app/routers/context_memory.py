"""
Context & Memory router — save/get/update/delete context, attach/detach
memory references, context window.
Matches the Context & Memory section of the Conversations & Chat APIs
blueprint (8/8).
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.context_memory import (
    ContextSaveRequest,
    ContextUpdateRequest,
    ContextOut,
    MemoryAttachRequest,
    MemoryDetachRequest,
    MemoryReferenceOut,
    ContextWindowRequest,
    ContextWindowOut,
)
from app.models.user import context_db, memory_references_db, context_window_db
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1", tags=["Context & Memory"])

DEFAULT_WINDOW_SIZE = 4096


def _require_owner(entry: dict, email: str):
    if entry["owner_email"] != email:
        raise HTTPException(status_code=403, detail="Only the owner can perform this action")


@router.post("/context/save", response_model=ContextOut, status_code=201)
def save_context(
    data: ContextSaveRequest,
    current_user: dict = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)
    context_db[data.conversation_id] = {
        "data": data.data,
        "owner_email": current_user["email"],
        "updated_at": now,
    }
    return ContextOut(conversation_id=data.conversation_id, data=data.data, updated_at=now)


@router.get("/context", response_model=ContextOut)
def get_context(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
):
    entry = context_db.get(conversation_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Context not found")
    _require_owner(entry, current_user["email"])
    return ContextOut(conversation_id=conversation_id, data=entry["data"], updated_at=entry["updated_at"])


@router.post("/context/update", response_model=ContextOut)
def update_context(
    data: ContextUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    entry = context_db.get(data.conversation_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Context not found")
    _require_owner(entry, current_user["email"])
    entry["data"].update(data.data)
    entry["updated_at"] = datetime.now(timezone.utc)
    return ContextOut(conversation_id=data.conversation_id, data=entry["data"], updated_at=entry["updated_at"])


@router.delete("/context", status_code=204)
def delete_context(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
):
    entry = context_db.get(conversation_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Context not found")
    _require_owner(entry, current_user["email"])
    del context_db[conversation_id]
    return None


@router.post("/memory/attach", response_model=MemoryReferenceOut, status_code=201)
def attach_memory(
    data: MemoryAttachRequest,
    current_user: dict = Depends(get_current_user),
):
    reference = {
        "id": str(uuid4()),
        "memory_id": data.memory_id,
        "label": data.label,
        "attached_at": datetime.now(timezone.utc),
    }
    memory_references_db.setdefault(data.conversation_id, []).append(reference)
    return reference


@router.post("/memory/detach", status_code=204)
def detach_memory(
    data: MemoryDetachRequest,
    current_user: dict = Depends(get_current_user),
):
    refs = memory_references_db.get(data.conversation_id, [])
    match = next((r for r in refs if r["id"] == data.reference_id), None)
    if not match:
        raise HTTPException(status_code=404, detail="Memory reference not found")
    refs.remove(match)
    return None


@router.get("/memory/references", response_model=list[MemoryReferenceOut])
def list_memory_references(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
):
    return memory_references_db.get(conversation_id, [])


@router.post("/context/window", response_model=ContextWindowOut)
def set_context_window(
    data: ContextWindowRequest,
    current_user: dict = Depends(get_current_user),
):
    size = data.window_size if data.window_size is not None else DEFAULT_WINDOW_SIZE
    context_window_db[data.conversation_id] = {
        "window_size": size,
        "updated_at": datetime.now(timezone.utc),
    }
    return ContextWindowOut(conversation_id=data.conversation_id, window_size=size)