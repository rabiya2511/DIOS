"""
Pydantic schemas for the AI Chat: Knowledge & RAG domain.
Simulated retrieval — no real vector DB/embedding pipeline exists yet.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class RagSearchRequest(BaseModel):
    query: str
    top_k: int = 5


class RagResultOut(BaseModel):
    source_id: str
    title: str
    snippet: str
    score: float


class RagRetrieveRequest(BaseModel):
    query: str
    top_k: int = 5


class RagRerankRequest(BaseModel):
    query: str
    results: list[RagResultOut]


class RagIndexRequest(BaseModel):
    title: str
    content: str


class RagSourceOut(BaseModel):
    id: str
    title: str
    indexed_at: datetime
    created_at: datetime


class RagUploadRequest(BaseModel):
    title: str
    content: str


class RagRemoveRequest(BaseModel):
    source_id: str


class RagRefreshResponse(BaseModel):
    refreshed_count: int
    timestamp: datetime