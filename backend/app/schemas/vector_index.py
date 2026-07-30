"""
Pydantic schemas for the Vector Index domain (Knowledge / RAG APIs
blueprint).

Everything here is SIMULATED — no real embedding vectors, no real vector
database (FAISS, Pinecone, pgvector, etc.) backs any of this. See router
docstring.
"""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel

IndexStatus = Literal["empty", "ready"]


class VectorIndexBuildRequest(BaseModel):
    source_ids: List[str] = []
    dimensions: int = 1536


class VectorIndexOut(BaseModel):
    status: IndexStatus
    vector_count: int
    dimensions: int
    size_mb: float
    owner_email: str
    last_indexed_at: Optional[datetime] = None
    last_optimized_at: Optional[datetime] = None
    last_compacted_at: Optional[datetime] = None


class VectorIndexStatsResponse(BaseModel):
    status: IndexStatus
    vector_count: int
    dimensions: int
    size_mb: float
    last_indexed_at: Optional[datetime] = None
    last_optimized_at: Optional[datetime] = None
    last_compacted_at: Optional[datetime] = None
    snapshot_count: int


class VectorSnapshotResponse(BaseModel):
    id: str
    vector_count: int
    size_mb: float
    created_at: datetime