"""
Pydantic schemas for the Context domain (Memory APIs blueprint).
Per-user context blob, distinct from context_memory.py's
conversation-scoped /api/v1/context (different path: /memory/context).
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class MemoryContextSetRequest(BaseModel):
    data: dict[str, Any]


class MemoryContextResponse(BaseModel):
    data: dict[str, Any]
    window_size: int | None = None
    updated_at: datetime | None = None


class MemoryContextDeleteResponse(BaseModel):
    cleared: bool


class ContextWindowRequest(BaseModel):
    window_size: int


class ContextWindowResponse(BaseModel):
    window_size: int
    updated_at: datetime


class ContextTrimResponse(BaseModel):
    original_length: int
    trimmed_length: int
    data: dict[str, Any]