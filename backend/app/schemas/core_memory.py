"""
Pydantic schemas for the Core Memory domain (Memory APIs blueprint).
"""

from datetime import datetime
from typing import Any, Dict, Optional, Literal

from pydantic import BaseModel

MemoryStatus = Literal["active", "archived"]


class MemoryCreateRequest(BaseModel):
    content: str
    memory_type: str = "general"
    metadata: Dict[str, Any] = {}


class MemoryUpdateRequest(BaseModel):
    content: Optional[str] = None
    memory_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class MemoryOut(BaseModel):
    id: str
    content: str
    memory_type: str
    metadata: Dict[str, Any]
    status: MemoryStatus
    owner_email: str
    created_at: datetime
    updated_at: datetime


class MemoryIdBodyRequest(BaseModel):
    memory_id: str