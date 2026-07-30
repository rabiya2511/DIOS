"""
Pydantic schemas for the Chunking domain (Knowledge / RAG APIs
blueprint). Accepts raw text directly via source_id + text, since the
Knowledge Base / Documents domains aren't built yet — self-contained
and testable independently.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

JobStatus = Literal["completed", "cancelled"]


class ChunkingRunRequest(BaseModel):
    source_id: str
    text: str


class ChunkingJobResponse(BaseModel):
    id: str
    source_id: str
    status: JobStatus
    chunks: list[str]
    chunk_count: int
    created_at: datetime
    completed_at: datetime | None = None


class ChunkingJobListResponse(BaseModel):
    total: int
    items: list[ChunkingJobResponse]


class RechunkRequest(BaseModel):
    job_id: str


class PreviewRequest(BaseModel):
    text: str


class PreviewResponse(BaseModel):
    chunks: list[str]
    chunk_count: int


class ChunkingConfigRequest(BaseModel):
    chunk_size: int = 200
    chunk_overlap: int = 20
    strategy: str = "fixed"


class ChunkingConfigResponse(BaseModel):
    chunk_size: int
    chunk_overlap: int
    strategy: str


class CancelJobRequest(BaseModel):
    job_id: str