"""
Chunking router — run, list jobs, get job, rechunk, preview, config,
cancel. Matches the Chunking section of the Knowledge / RAG APIs
blueprint (8/8). STUBBED: character-based splitting (no real
tokenizer-aware chunking), synchronous "jobs" (no real async queue).

No ordering conflicts: GET /jobs vs GET /jobs/{id} differ in segment
count; /config, /run, /rechunk, /preview, /cancel are all fixed
literal paths.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.chunking import (
    ChunkingRunRequest,
    ChunkingJobResponse,
    ChunkingJobListResponse,
    RechunkRequest,
    PreviewRequest,
    PreviewResponse,
    ChunkingConfigRequest,
    ChunkingConfigResponse,
    CancelJobRequest,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/chunking", tags=["Chunking"])

# id -> {id, owner_email, source_id, original_text, status, chunks, chunk_count, created_at, completed_at}
chunking_jobs_db: dict[str, dict] = {}

# email -> {chunk_size, chunk_overlap, strategy}
chunking_config_db: dict[str, dict] = {}

DEFAULT_CONFIG = {"chunk_size": 200, "chunk_overlap": 20, "strategy": "fixed"}


def _get_or_create_config(email: str) -> dict:
    return chunking_config_db.setdefault(email, dict(DEFAULT_CONFIG))


def _split_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    if chunk_size <= 0:
        return [text] if text else []
    step = max(chunk_size - chunk_overlap, 1)
    chunks = []
    i = 0
    while i < len(text):
        chunks.append(text[i:i + chunk_size])
        i += step
    return chunks


def _get_owned_job(job_id: str, email: str) -> dict:
    job = chunking_jobs_db.get(job_id)
    if not job or job["owner_email"] != email:
        raise HTTPException(status_code=404, detail="Chunking job not found")
    return job


@router.post("/run", response_model=ChunkingJobResponse, status_code=201)
def run_chunking(data: ChunkingRunRequest, current_user: dict = Depends(get_current_user)):
    config = _get_or_create_config(current_user["email"])
    chunks = _split_text(data.text, config["chunk_size"], config["chunk_overlap"])

    job_id = str(uuid4())
    now = datetime.now(timezone.utc)
    chunking_jobs_db[job_id] = {
        "id": job_id,
        "owner_email": current_user["email"],
        "source_id": data.source_id,
        "original_text": data.text,
        "status": "completed",
        "chunks": chunks,
        "chunk_count": len(chunks),
        "created_at": now,
        "completed_at": now,
    }
    return chunking_jobs_db[job_id]


@router.get("/jobs", response_model=ChunkingJobListResponse)
def list_jobs(current_user: dict = Depends(get_current_user)):
    items = [j for j in chunking_jobs_db.values() if j["owner_email"] == current_user["email"]]
    return ChunkingJobListResponse(total=len(items), items=items)


@router.get("/jobs/{id}", response_model=ChunkingJobResponse)
def get_job(id: str, current_user: dict = Depends(get_current_user)):
    return _get_owned_job(id, current_user["email"])


@router.post("/rechunk", response_model=ChunkingJobResponse)
def rechunk(data: RechunkRequest, current_user: dict = Depends(get_current_user)):
    job = _get_owned_job(data.job_id, current_user["email"])
    config = _get_or_create_config(current_user["email"])
    chunks = _split_text(job["original_text"], config["chunk_size"], config["chunk_overlap"])

    job["chunks"] = chunks
    job["chunk_count"] = len(chunks)
    job["completed_at"] = datetime.now(timezone.utc)
    return job


@router.post("/preview", response_model=PreviewResponse)
def preview_chunking(data: PreviewRequest, current_user: dict = Depends(get_current_user)):
    config = _get_or_create_config(current_user["email"])
    chunks = _split_text(data.text, config["chunk_size"], config["chunk_overlap"])
    return PreviewResponse(chunks=chunks, chunk_count=len(chunks))


@router.post("/config", response_model=ChunkingConfigResponse)
def set_config(data: ChunkingConfigRequest, current_user: dict = Depends(get_current_user)):
    chunking_config_db[current_user["email"]] = {
        "chunk_size": data.chunk_size,
        "chunk_overlap": data.chunk_overlap,
        "strategy": data.strategy,
    }
    return chunking_config_db[current_user["email"]]


@router.get("/config", response_model=ChunkingConfigResponse)
def get_config(current_user: dict = Depends(get_current_user)):
    return _get_or_create_config(current_user["email"])


@router.post("/cancel", response_model=ChunkingJobResponse)
def cancel_job(data: CancelJobRequest, current_user: dict = Depends(get_current_user)):
    job = _get_owned_job(data.job_id, current_user["email"])
    job["status"] = "cancelled"
    return job