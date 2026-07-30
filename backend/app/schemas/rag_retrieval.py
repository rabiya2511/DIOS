"""
Pydantic schemas for the Retrieval domain (Knowledge / RAG APIs
blueprint).

Everything here is SIMULATED — no real document corpus, no real
embeddings, no real search index backs any of this. See router
docstring.
"""

from datetime import datetime
from typing import Dict, List

from pydantic import BaseModel


class RagResultItem(BaseModel):
    id: str
    source_id: str
    content_snippet: str
    score: float


class RagSearchRequest(BaseModel):
    query: str
    top_k: int = 5


class RagSearchResponse(BaseModel):
    query: str
    method: str
    results: List[RagResultItem]
    created_at: datetime


class RagFilterRequest(BaseModel):
    query: str
    filters: Dict[str, str] = {}
    top_k: int = 5


class RagQueryRequest(BaseModel):
    query: str
    top_k: int = 5


class RagQueryResponse(BaseModel):
    query: str
    results: List[RagResultItem]
    answer: str
    created_at: datetime


class RagHybridSearchRequest(BaseModel):
    query: str
    top_k: int = 5
    keyword_weight: float = 0.5


class RagHistoryEntry(BaseModel):
    id: str
    endpoint: str
    query: str
    result_count: int
    created_at: datetime