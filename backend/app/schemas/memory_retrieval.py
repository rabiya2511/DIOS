"""
Schemas for the Retrieval group of the Memory APIs blueprint.
Reuses MemoryOut from core_memory's schema, since retrieval always
returns the same memory entries core_memory owns — no separate
memory-entry shape defined here.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Literal

from pydantic import BaseModel, Field

from app.schemas.core_memory import MemoryOut


class MemorySearchRequest(BaseModel):
    query: str
    memory_type: Optional[str] = None
    limit: int = Field(20, ge=1, le=200)


class MemorySearchResult(BaseModel):
    id: str
    content: str
    memory_type: str
    metadata: Dict[str, Any]
    status: str
    score: float


class MemorySearchResponse(BaseModel):
    query: str
    total: int
    results: List[MemorySearchResult]


class MemoryRetrieveRequest(BaseModel):
    memory_ids: List[str]


class MemoryRetrieveResponse(BaseModel):
    total: int
    items: List[MemoryOut]


class MemoryFilterRequest(BaseModel):
    memory_type: Optional[str] = None
    status: Optional[Literal["active", "archived"]] = None
    metadata_filters: Dict[str, Any] = Field(
        default_factory=dict, description="Exact-match key/value pairs checked against metadata"
    )
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None


class MemoryFilterResponse(BaseModel):
    total: int
    items: List[MemoryOut]


class MemoryRerankRequest(BaseModel):
    query: str
    memory_ids: Optional[List[str]] = Field(
        None, description="Subset of memory_ids to rerank; omit to rerank all owned memories"
    )


class MemoryRerankResult(BaseModel):
    id: str
    content: str
    score: float = Field(..., ge=0.0, le=1.0)


class MemoryRerankResponse(BaseModel):
    query: str
    results: List[MemoryRerankResult]


class RecentMemoriesResponse(BaseModel):
    total: int
    items: List[MemoryOut]


class FavoriteMemoriesResponse(BaseModel):
    total: int
    items: List[MemoryOut]