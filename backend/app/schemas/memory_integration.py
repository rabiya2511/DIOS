"""
Schemas for the Memory Integration group of the Agents & Planning APIs
blueprint.
"""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, EmailStr, Field


class MemoryAttachRequest(BaseModel):
    agent_id: str
    memory_id: str = Field(..., description="ID of the memory item being attached")
    label: Optional[str] = None
    content: Optional[str] = Field(None, description="Snapshot of the memory's content, used for search/summarize")


class MemoryDetachRequest(BaseModel):
    agent_id: str
    memory_id: str


class MemoryDetachResponse(BaseModel):
    agent_id: str
    memory_id: str
    detached: bool


class AgentMemoryResponse(BaseModel):
    id: str
    owner_email: EmailStr
    agent_id: str
    memory_id: str
    label: Optional[str] = None
    content: Optional[str] = None
    attached_at: datetime
    updated_at: datetime


class AgentMemoryListResponse(BaseModel):
    total: int
    items: List[AgentMemoryResponse]


class MemorySearchRequest(BaseModel):
    query: str
    agent_id: Optional[str] = Field(None, description="Restrict search to one agent's memories")


class MemorySearchResult(BaseModel):
    id: str
    agent_id: str
    memory_id: str
    label: Optional[str] = None
    content: Optional[str] = None
    score: float


class MemorySearchResponse(BaseModel):
    query: str
    total: int
    results: List[MemorySearchResult]


class MemoryUpdateRequest(BaseModel):
    agent_id: str
    memory_id: str
    label: Optional[str] = None
    content: Optional[str] = None


class MemorySummarizeRequest(BaseModel):
    agent_id: str


class MemorySummarizeResponse(BaseModel):
    agent_id: str
    memory_count: int
    summary: str
    summarized_at: datetime


class ContextBuildRequest(BaseModel):
    agent_id: str
    memory_ids: Optional[List[str]] = Field(
        None, description="Subset of attached memory_ids to include; omit to use all attached memories"
    )
    max_items: int = Field(20, ge=1, le=200)


class ContextBuildResponse(BaseModel):
    agent_id: str
    context: str
    memory_ids_used: List[str]
    built_at: datetime


class ContextClearRequest(BaseModel):
    agent_id: str


class ContextClearResponse(BaseModel):
    agent_id: str
    cleared: bool
    cleared_at: datetime