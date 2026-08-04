"""
Context router — get/set/update/clear context, window, trim.
Matches the Context section of the Memory APIs blueprint (6/6).
Per-user context blob, distinct from context_memory.py's
conversation-scoped /api/v1/context (different path: /memory/context,
no collision).
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.schemas.memory_context import (
    MemoryContextSetRequest,
    MemoryContextResponse,
    MemoryContextDeleteResponse,
    ContextWindowRequest,
    ContextWindowResponse,
    ContextTrimResponse,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/memory/context", tags=["Memory Context"])

# email -> {data, window_size, updated_at}
memory_context_db: dict[str, dict] = {}


def _get_or_create(email: str) -> dict:
    return memory_context_db.setdefault(email, {"data": {}, "window_size": None, "updated_at": None})


@router.get("", response_model=MemoryContextResponse)
def get_context(current_user: dict = Depends(get_current_user)):
    return _get_or_create(current_user["email"])


@router.post("", response_model=MemoryContextResponse)
def set_context(data: MemoryContextSetRequest, current_user: dict = Depends(get_current_user)):
    ctx = _get_or_create(current_user["email"])
    ctx["data"] = data.data
    ctx["updated_at"] = datetime.now(timezone.utc)
    return ctx


@router.patch("", response_model=MemoryContextResponse)
def update_context(data: MemoryContextSetRequest, current_user: dict = Depends(get_current_user)):
    ctx = _get_or_create(current_user["email"])
    ctx["data"].update(data.data)
    ctx["updated_at"] = datetime.now(timezone.utc)
    return ctx


@router.delete("", response_model=MemoryContextDeleteResponse)
def clear_context(current_user: dict = Depends(get_current_user)):
    existed = current_user["email"] in memory_context_db
    memory_context_db.pop(current_user["email"], None)
    return MemoryContextDeleteResponse(cleared=existed)


@router.post("/window", response_model=ContextWindowResponse)
def set_window(data: ContextWindowRequest, current_user: dict = Depends(get_current_user)):
    ctx = _get_or_create(current_user["email"])
    ctx["window_size"] = data.window_size
    now = datetime.now(timezone.utc)
    ctx["updated_at"] = now
    return ContextWindowResponse(window_size=data.window_size, updated_at=now)


@router.post("/trim", response_model=ContextTrimResponse)
def trim_context(current_user: dict = Depends(get_current_user)):
    ctx = _get_or_create(current_user["email"])
    original_length = len(ctx["data"])
    window_size = ctx["window_size"] or original_length

    items = list(ctx["data"].items())
    trimmed_items = items[-window_size:] if window_size > 0 else []
    ctx["data"] = dict(trimmed_items)
    ctx["updated_at"] = datetime.now(timezone.utc)

    return ContextTrimResponse(
        original_length=original_length,
        trimmed_length=len(ctx["data"]),
        data=ctx["data"],
    )