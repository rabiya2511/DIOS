"""
Conversation Memory router — list/create/update/delete conversation
memory entries, summarize, history.
Matches the Conversation Memory section of the Memory APIs blueprint
(6/6).

*** ROUTING NOTE — READ THIS FIRST ***
This router's base path (GET/POST /api/v1/memory/conversations) is a
SINGLE-SEGMENT literal path under /api/v1/memory — the same shape as
core_memory.py's dynamic GET/PATCH/DELETE /api/v1/memory/{id}. This
router MUST be registered in main.py BEFORE core_memory.router, or
GET /memory/conversations would be swallowed by core_memory's /{id}
route (treating "conversations" as a memory id).

WHAT'S REAL VS. STUB HERE:
- POST /memory/conversations/summarize is a STUB: it does NOT call any
  summarization model. It naively concatenates the provided messages and
  truncates to ~200 characters. This is enough to exercise the API
  contract, not to produce a real summary. Swap in a real model call
  before relying on this for anything real.
- Everything else (create/list/update/delete/history) is genuine CRUD
  over real stored data, scoped to the caller (owner_email).

ASSUMPTIONS:
- The {id} in PATCH/DELETE /memory/conversations/{id} refers to the
  memory ENTRY's own id, not the conversation_id — a single
  conversation_id can have multiple memory entries (notes, summaries,
  etc.) attached to it over time.
- GET /memory/conversations/history requires a ?conversation_id= query
  param and returns every memory entry recorded for that conversation
  (owned by the caller), newest first.
- /summarize and /history are literal paths registered BEFORE this
  router's own /{id} route, for the same internal-ordering reason as
  fileslifecycle.py's /archive, /restore, /clone.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query

from app.schemas.conversation_memory import (
    ConversationMemoryCreateRequest,
    ConversationMemoryUpdateRequest,
    ConversationMemoryOut,
    SummarizeRequest,
    HistoryQueryResponse,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/memory/conversations", tags=["Conversation Memory"])

# id -> {id, conversation_id, content, memory_type, owner_email, created_at, updated_at}
conversation_memory_db: dict[str, dict] = {}


def _get_entry_or_404(id: str) -> dict:
    entry = conversation_memory_db.get(id)
    if not entry:
        raise HTTPException(status_code=404, detail="Conversation memory entry not found")
    return entry


def _require_owner(entry: dict, email: str):
    if entry["owner_email"] != email:
        raise HTTPException(status_code=403, detail="Only the owner can perform this action")


def _stub_summarize(messages: list[str]) -> str:
    """STUB — naive concatenation + truncation, not a real summarization model."""
    joined = " ".join(messages).strip()
    if not joined:
        return "[stub summary] No messages provided to summarize."
    truncated = joined[:200]
    suffix = "..." if len(joined) > 200 else ""
    return f"[stub summary] {truncated}{suffix}"


@router.get("", response_model=list[ConversationMemoryOut])
def list_conversation_memory(
    conversation_id: str | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
):
    entries = [e for e in conversation_memory_db.values() if e["owner_email"] == current_user["email"]]
    if conversation_id is not None:
        entries = [e for e in entries if e["conversation_id"] == conversation_id]
    return entries


@router.post("", response_model=ConversationMemoryOut, status_code=201)
def create_conversation_memory(
    data: ConversationMemoryCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    entry_id = str(uuid4())
    now = datetime.now(timezone.utc)
    conversation_memory_db[entry_id] = {
        "id": entry_id,
        "conversation_id": data.conversation_id,
        "content": data.content,
        "memory_type": data.memory_type,
        "owner_email": current_user["email"],
        "created_at": now,
        "updated_at": now,
    }
    return conversation_memory_db[entry_id]


# ─── Literal-path routes MUST come before any /{id} routes below ───

@router.post("/summarize", response_model=ConversationMemoryOut, status_code=201)
def summarize_conversation(data: SummarizeRequest, current_user: dict = Depends(get_current_user)):
    entry_id = str(uuid4())
    now = datetime.now(timezone.utc)
    conversation_memory_db[entry_id] = {
        "id": entry_id,
        "conversation_id": data.conversation_id,
        "content": _stub_summarize(data.messages),
        "memory_type": "summary",
        "owner_email": current_user["email"],
        "created_at": now,
        "updated_at": now,
    }
    return conversation_memory_db[entry_id]


@router.get("/history", response_model=HistoryQueryResponse)
def get_conversation_history(
    conversation_id: str = Query(...),
    current_user: dict = Depends(get_current_user),
):
    entries = [
        e for e in conversation_memory_db.values()
        if e["owner_email"] == current_user["email"] and e["conversation_id"] == conversation_id
    ]
    entries_sorted = sorted(entries, key=lambda e: e["created_at"], reverse=True)
    return HistoryQueryResponse(conversation_id=conversation_id, entries=entries_sorted)


# ─── Dynamic /{id} routes come LAST ───

@router.patch("/{id}", response_model=ConversationMemoryOut)
def update_conversation_memory(
    id: str,
    data: ConversationMemoryUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    entry = _get_entry_or_404(id)
    _require_owner(entry, current_user["email"])
    if data.content is not None:
        entry["content"] = data.content
    if data.memory_type is not None:
        entry["memory_type"] = data.memory_type
    entry["updated_at"] = datetime.now(timezone.utc)
    return entry


@router.delete("/{id}", status_code=204)
def delete_conversation_memory(id: str, current_user: dict = Depends(get_current_user)):
    entry = _get_entry_or_404(id)
    _require_owner(entry, current_user["email"])
    del conversation_memory_db[id]
    return None