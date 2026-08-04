"""
Core Memory router — CRUD, archive.
Matches the Core Memory section of the Memory APIs blueprint (6/6).
Only the memory owner can update/delete/archive their own memory entry.
Mirrors the structure of projects.py / prompts.py.

NOTE: unlike most other domains in this codebase, this blueprint section
has NO /restore endpoint — archiving is one-way here (matches the
blueprint exactly: GET/POST/PATCH/DELETE /memory[/{id}] plus POST
/memory/archive, and nothing else). If you want restore capability, that
would need to be added as a follow-up beyond what this blueprint section
specifies.

Literal-path routes (/archive) MUST come before the dynamic /{id} routes
below — same ordering rule used throughout this codebase.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.core_memory import (
    MemoryCreateRequest,
    MemoryUpdateRequest,
    MemoryOut,
    MemoryIdBodyRequest,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/memory", tags=["Core Memory"])

# id -> {id, content, memory_type, metadata, status, owner_email, created_at, updated_at}
memory_db: dict[str, dict] = {}


def _get_memory_or_404(id: str) -> dict:
    memory = memory_db.get(id)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory entry not found")
    return memory


def _require_owner(memory: dict, email: str):
    if memory["owner_email"] != email:
        raise HTTPException(status_code=403, detail="Only the memory owner can perform this action")


@router.get("", response_model=list[MemoryOut])
def list_memory(current_user: dict = Depends(get_current_user)):
    return [m for m in memory_db.values() if m["owner_email"] == current_user["email"]]


@router.post("", response_model=MemoryOut, status_code=201)
def create_memory(data: MemoryCreateRequest, current_user: dict = Depends(get_current_user)):
    memory_id = str(uuid4())
    now = datetime.now(timezone.utc)
    memory_db[memory_id] = {
        "id": memory_id,
        "content": data.content,
        "memory_type": data.memory_type,
        "metadata": data.metadata,
        "status": "active",
        "owner_email": current_user["email"],
        "created_at": now,
        "updated_at": now,
    }
    return memory_db[memory_id]


# ─── Literal-path routes MUST come before any /{id} routes below ───

@router.post("/archive", response_model=MemoryOut)
def archive_memory(data: MemoryIdBodyRequest, current_user: dict = Depends(get_current_user)):
    memory = _get_memory_or_404(data.memory_id)
    _require_owner(memory, current_user["email"])
    memory["status"] = "archived"
    memory["updated_at"] = datetime.now(timezone.utc)
    return memory


# ─── Dynamic /{id} routes come LAST ───

@router.get("/{id}", response_model=MemoryOut)
def get_memory(id: str, current_user: dict = Depends(get_current_user)):
    memory = _get_memory_or_404(id)
    _require_owner(memory, current_user["email"])
    return memory


@router.patch("/{id}", response_model=MemoryOut)
def update_memory(id: str, data: MemoryUpdateRequest, current_user: dict = Depends(get_current_user)):
    memory = _get_memory_or_404(id)
    _require_owner(memory, current_user["email"])
    if data.content is not None:
        memory["content"] = data.content
    if data.memory_type is not None:
        memory["memory_type"] = data.memory_type
    if data.metadata is not None:
        memory["metadata"] = data.metadata
    memory["updated_at"] = datetime.now(timezone.utc)
    return memory


@router.delete("/{id}", status_code=204)
def delete_memory(id: str, current_user: dict = Depends(get_current_user)):
    memory = _get_memory_or_404(id)
    _require_owner(memory, current_user["email"])
    del memory_db[id]
    return None