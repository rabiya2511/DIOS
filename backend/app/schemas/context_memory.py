"""
Pydantic schemas for the Context & Memory domain.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ContextSaveRequest(BaseModel):
    conversation_id: str
    data: dict


class ContextUpdateRequest(BaseModel):
    conversation_id: str
    data: dict


class ContextOut(BaseModel):
    conversation_id: str
    data: dict
    updated_at: datetime


class MemoryAttachRequest(BaseModel):
    conversation_id: str
    memory_id: str
    label: Optional[str] = None


class MemoryDetachRequest(BaseModel):
    conversation_id: str
    reference_id: str


class MemoryReferenceOut(BaseModel):
    id: str
    memory_id: str
    label: Optional[str] = None
    attached_at: datetime


class ContextWindowRequest(BaseModel):
    conversation_id: str
    window_size: Optional[int] = None


class ContextWindowOut(BaseModel):
    conversation_id: str
    window_size: int