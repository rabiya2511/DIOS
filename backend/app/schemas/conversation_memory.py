"""
Pydantic schemas for the Conversation Memory domain (Memory APIs
blueprint).
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class ConversationMemoryCreateRequest(BaseModel):
    conversation_id: str
    content: str
    memory_type: str = "note"


class ConversationMemoryUpdateRequest(BaseModel):
    content: Optional[str] = None
    memory_type: Optional[str] = None


class ConversationMemoryOut(BaseModel):
    id: str
    conversation_id: str
    content: str
    memory_type: str
    owner_email: str
    created_at: datetime
    updated_at: datetime


class SummarizeRequest(BaseModel):
    conversation_id: str
    messages: List[str] = []


class HistoryQueryResponse(BaseModel):
    conversation_id: str
    entries: List[ConversationMemoryOut]