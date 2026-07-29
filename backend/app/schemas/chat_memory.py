"""
Pydantic schemas for the AI Chat: Memory domain.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class MemorySaveRequest(BaseModel):
    content: str
    chat_id: Optional[str] = None
    tags: list[str] = []


class MemoryOut(BaseModel):
    id: str
    owner_email: str
    chat_id: Optional[str] = None
    content: str
    tags: list[str]
    created_at: datetime
    updated_at: datetime


class MemorySearchRequest(BaseModel):
    query: str


class MemoryUpdateRequest(BaseModel):
    memory_id: str
    content: Optional[str] = None
    tags: Optional[list[str]] = None


class MemoryDeleteRequest(BaseModel):
    memory_id: str


class MemoryImportRequest(BaseModel):
    memories: list[MemorySaveRequest]


class MemorySummarizeRequest(BaseModel):
    chat_id: Optional[str] = None


class MemorySummarizeResponse(BaseModel):
    summary: str
    memory_count: int