"""
Pydantic schemas for the Embeddings domain (Knowledge / RAG APIs
blueprint). STUBBED: vectors are deterministic fake floats derived
from text length/hash, not real embedding model output.
"""

from datetime import datetime

from pydantic import BaseModel


class EmbeddingModelResponse(BaseModel):
    id: str
    name: str
    dimensions: int


class EmbeddingCreateRequest(BaseModel):
    text: str
    model_id: str | None = None  # defaults to the user's selected model


class EmbeddingUpdateRequest(BaseModel):
    embedding_id: str
    text: str


class EmbeddingDeleteRequest(BaseModel):
    embedding_id: str


class EmbeddingResponse(BaseModel):
    id: str
    source_text: str
    model_id: str
    vector: list[float]
    created_at: datetime


class EmbeddingDeleteResponse(BaseModel):
    deleted: bool


class RebuildResponse(BaseModel):
    rebuilt_count: int
    completed_at: datetime


class SelectModelRequest(BaseModel):
    model_id: str


class EmbeddingStatsResponse(BaseModel):
    total_embeddings: int
    current_model_id: str
    average_dimensions: float


class BatchEmbeddingRequest(BaseModel):
    texts: list[str]
    model_id: str | None = None


class BatchEmbeddingResponse(BaseModel):
    created: int
    embeddings: list[EmbeddingResponse]