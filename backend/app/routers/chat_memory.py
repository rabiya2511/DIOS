"""
Memory router — save, get, search, update, delete, import, export, summarize.
Matches the Memory section of the AI Chat APIs blueprint (8/8).
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.chat_memory import (
    MemorySaveRequest,
    MemoryOut,
    MemorySearchRequest,
    MemoryUpdateRequest,
    MemoryDeleteRequest,
    MemoryImportRequest,
    MemorySummarizeRequest,
    MemorySummarizeResponse,
)
from app.models.user import chat_memories_db
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/chat/memory", tags=["AI Chat: Memory"])


def _get_owned_memory(memory_id: str, current_user: dict) -> dict:
    mem = chat_memories_db.get(memory_id)
    if not mem:
        raise HTTPException(status_code=404, detail="Memory not found")
    if mem["owner_email"] != current_user["email"]:
        raise HTTPException(status_code=403, detail="Only the memory owner can perform this action")
    return mem


@router.post("/save", response_model=MemoryOut, status_code=201)
def save_memory(
    data: MemorySaveRequest,
    current_user: dict = Depends(get_current_user),
):
    memory_id = str(uuid4())
    now = datetime.now(timezone.utc)
    memory = {
        "id": memory_id,
        "owner_email": current_user["email"],
        "chat_id": data.chat_id,
        "content": data.content,
        "tags": data.tags,
        "created_at": now,
        "updated_at": now,
    }
    chat_memories_db[memory_id] = memory
    return memory


@router.get("", response_model=list[MemoryOut])
def list_memories(current_user: dict = Depends(get_current_user)):
    return [m for m in chat_memories_db.values() if m["owner_email"] == current_user["email"]]


@router.post("/search", response_model=list[MemoryOut])
def search_memories(
    data: MemorySearchRequest,
    current_user: dict = Depends(get_current_user),
):
    query = data.query.lower()
    email = current_user["email"]
    return [
        m for m in chat_memories_db.values()
        if m["owner_email"] == email
        and (query in m["content"].lower() or any(query in t.lower() for t in m["tags"]))
    ]


@router.post("/update", response_model=MemoryOut)
def update_memory(
    data: MemoryUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    mem = _get_owned_memory(data.memory_id, current_user)
    if data.content is not None:
        mem["content"] = data.content
    if data.tags is not None:
        mem["tags"] = data.tags
    mem["updated_at"] = datetime.now(timezone.utc)
    return mem


@router.post("/delete", status_code=204)
def delete_memory(
    data: MemoryDeleteRequest,
    current_user: dict = Depends(get_current_user),
):
    mem = _get_owned_memory(data.memory_id, current_user)
    del chat_memories_db[mem["id"]]
    return None


@router.post("/import", response_model=list[MemoryOut], status_code=201)
def import_memories(
    data: MemoryImportRequest,
    current_user: dict = Depends(get_current_user),
):
    imported = []
    now = datetime.now(timezone.utc)
    for item in data.memories:
        memory_id = str(uuid4())
        memory = {
            "id": memory_id,
            "owner_email": current_user["email"],
            "chat_id": item.chat_id,
            "content": item.content,
            "tags": item.tags,
            "created_at": now,
            "updated_at": now,
        }
        chat_memories_db[memory_id] = memory
        imported.append(memory)
    return imported


@router.post("/export", response_model=list[MemoryOut])
def export_memories(current_user: dict = Depends(get_current_user)):
    return [m for m in chat_memories_db.values() if m["owner_email"] == current_user["email"]]


@router.post("/summarize", response_model=MemorySummarizeResponse)
def summarize_memories(
    data: MemorySummarizeRequest,
    current_user: dict = Depends(get_current_user),
):
    email = current_user["email"]
    memories = [m for m in chat_memories_db.values() if m["owner_email"] == email]
    if data.chat_id:
        memories = [m for m in memories if m["chat_id"] == data.chat_id]

    # STUB: real version would call the model to synthesize an actual summary.
    summary = f"[stubbed] {len(memories)} memory entries covering topics: " + ", ".join(
        sorted({t for m in memories for t in m["tags"]})
    ) if memories else "[stubbed] No memories found."

    return MemorySummarizeResponse(summary=summary, memory_count=len(memories))