"""
Router for the Inference group of the Model Management APIs
blueprint.
  POST /api/v1/inference/chat
  POST /api/v1/inference/completion
  POST /api/v1/inference/embedding
  POST /api/v1/inference/image
  POST /api/v1/inference/audio
  POST /api/v1/inference/video
  POST /api/v1/inference/batch
  GET  /api/v1/inference/jobs

No dynamic /{id} route in this group per the blueprint, so there's no
literal-vs-dynamic ordering concern here (see evaluation.py /
conversations.py / fileslifecycle.py for that pattern elsewhere in
the API).

chat / completion / embedding / image / audio are synchronous —
they simulate model output and return it immediately. video and
batch are treated as longer-running jobs: they're created in
"queued" status and stored in an in-memory dict, retrievable (as a
list) via GET /inference/jobs. Only the job owner sees their own
jobs in that listing, same owner-scoping pattern as
evaluation_jobs_db in evaluation.py.

All outputs here are simulated (random/canned) — not computed by a
real model. Swap in a real inference backend before relying on this
for anything beyond local dev/API-shape testing.
"""

import random
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.schemas.model_inference import (
    ChatRequest,
    ChatResponse,
    ChatChoice,
    ChatMessage,
    CompletionRequest,
    CompletionResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    ImageRequest,
    ImageResponse,
    ImageItem,
    AudioRequest,
    AudioResponse,
    VideoRequest,
    VideoJobResponse,
    BatchRequest,
    BatchJobResponse,
    InferenceJobEntry,
    InferenceJobListResponse,
    UsageInfo,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/inference", tags=["Inference"])

# id -> job dict (video + batch jobs only; see module docstring)
# {id, type, owner_email, model_id, status, config, created_at, updated_at, ...}
inference_jobs_db: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# simulation helpers
# ---------------------------------------------------------------------------

def _simulate_usage(prompt_text: str, completion_text: str = "") -> UsageInfo:
    prompt_tokens = max(1, len(prompt_text) // 4)
    completion_tokens = max(1, len(completion_text) // 4) if completion_text else 0
    return UsageInfo(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
    )


def _simulate_chat_reply(messages: list[ChatMessage]) -> str:
    last_user = next((m.content for m in reversed(messages) if m.role == "user"), "")
    return f"Simulated reply to: {last_user[:80]}"


def _simulate_completion(prompt: str) -> str:
    return f"Simulated completion for: {prompt[:80]}"


def _simulate_embedding(dim: int = 8) -> list[float]:
    return [round(random.uniform(-1, 1), 4) for _ in range(dim)]


def _simulate_image_url(job_id: str, idx: int) -> str:
    return f"https://simulated-storage.local/images/{job_id}-{idx}.png"


def _simulate_audio_url(job_id: str, fmt: str) -> str:
    return f"https://simulated-storage.local/audio/{job_id}.{fmt}"


def _simulate_video_url(job_id: str) -> str:
    return f"https://simulated-storage.local/video/{job_id}.mp4"


# ---------------------------------------------------------------------------
# POST /api/v1/inference/chat
# ---------------------------------------------------------------------------
@router.post("/chat", response_model=ChatResponse, status_code=201)
def chat(
    payload: ChatRequest,
    current_user: dict = Depends(get_current_user),
):
    """Simulated chat completion for a list of messages."""
    reply_text = _simulate_chat_reply(payload.messages)
    prompt_text = " ".join(m.content for m in payload.messages)
    usage = _simulate_usage(prompt_text, reply_text)

    return ChatResponse(
        id=str(uuid.uuid4()),
        model_id=payload.model_id,
        owner_email=current_user["email"],
        choices=[
            ChatChoice(
                index=0,
                message=ChatMessage(role="assistant", content=reply_text),
                finish_reason="stop",
            )
        ],
        usage=usage,
        created_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# POST /api/v1/inference/completion
# ---------------------------------------------------------------------------
@router.post("/completion", response_model=CompletionResponse, status_code=201)
def completion(
    payload: CompletionRequest,
    current_user: dict = Depends(get_current_user),
):
    """Simulated text completion for a prompt."""
    text = _simulate_completion(payload.prompt)
    usage = _simulate_usage(payload.prompt, text)

    return CompletionResponse(
        id=str(uuid.uuid4()),
        model_id=payload.model_id,
        owner_email=current_user["email"],
        text=text,
        finish_reason="stop",
        usage=usage,
        created_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# POST /api/v1/inference/embedding
# ---------------------------------------------------------------------------
@router.post("/embedding", response_model=EmbeddingResponse, status_code=201)
def embedding(
    payload: EmbeddingRequest,
    current_user: dict = Depends(get_current_user),
):
    """Simulated embeddings for one string or a list of strings."""
    inputs = [payload.input] if isinstance(payload.input, str) else payload.input
    dim = 8
    vectors = [_simulate_embedding(dim) for _ in inputs]
    usage = _simulate_usage(" ".join(inputs))

    return EmbeddingResponse(
        id=str(uuid.uuid4()),
        model_id=payload.model_id,
        owner_email=current_user["email"],
        embeddings=vectors,
        dimensions=dim,
        usage=usage,
        created_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# POST /api/v1/inference/image
# ---------------------------------------------------------------------------
@router.post("/image", response_model=ImageResponse, status_code=201)
def image(
    payload: ImageRequest,
    current_user: dict = Depends(get_current_user),
):
    """Simulated image generation."""
    job_id = str(uuid.uuid4())
    images = [
        ImageItem(url=_simulate_image_url(job_id, i), revised_prompt=payload.prompt)
        for i in range(payload.n)
    ]

    return ImageResponse(
        id=job_id,
        model_id=payload.model_id,
        owner_email=current_user["email"],
        images=images,
        created_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# POST /api/v1/inference/audio
# ---------------------------------------------------------------------------
@router.post("/audio", response_model=AudioResponse, status_code=201)
def audio(
    payload: AudioRequest,
    current_user: dict = Depends(get_current_user),
):
    """Simulated text-to-speech audio generation."""
    job_id = str(uuid.uuid4())
    duration = round(max(0.5, len(payload.text) / 15), 1)

    return AudioResponse(
        id=job_id,
        model_id=payload.model_id,
        owner_email=current_user["email"],
        audio_url=_simulate_audio_url(job_id, payload.format),
        duration_seconds=duration,
        format=payload.format,
        created_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# POST /api/v1/inference/video
# ---------------------------------------------------------------------------
@router.post("/video", response_model=VideoJobResponse, status_code=202)
def video(
    payload: VideoRequest,
    current_user: dict = Depends(get_current_user),
):
    """Queue a simulated video generation job. Poll GET /inference/jobs for status."""
    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    job = {
        "id": job_id,
        "type": "video",
        "owner_email": current_user["email"],
        "model_id": payload.model_id,
        "status": "completed",  # simulated as immediately done
        "video_url": _simulate_video_url(job_id),
        "config": payload.model_dump(exclude={"model_id"}),
        "created_at": now,
        "updated_at": now,
    }
    inference_jobs_db[job_id] = job
    return job


# ---------------------------------------------------------------------------
# POST /api/v1/inference/batch
# ---------------------------------------------------------------------------
@router.post("/batch", response_model=BatchJobResponse, status_code=202)
def batch(
    payload: BatchRequest,
    current_user: dict = Depends(get_current_user),
):
    """Queue a simulated batch inference job covering multiple requests."""
    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    results = [
        {"custom_id": item.custom_id, "task_type": item.task_type, "output": "Simulated batch result"}
        for item in payload.requests
    ]
    job = {
        "id": job_id,
        "type": "batch",
        "owner_email": current_user["email"],
        "model_id": payload.model_id,
        "status": "completed",  # simulated as immediately done
        "request_count": len(payload.requests),
        "results": results,
        "config": payload.config,
        "created_at": now,
        "updated_at": now,
    }
    inference_jobs_db[job_id] = job
    return job


# ---------------------------------------------------------------------------
# GET /api/v1/inference/jobs
# ---------------------------------------------------------------------------
@router.get("/jobs", response_model=InferenceJobListResponse)
def list_inference_jobs(
    type_: Optional[str] = Query(None, alias="type"),
    model_id: Optional[str] = Query(None),
    status_: Optional[str] = Query(None, alias="status"),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    """List the caller's video/batch inference jobs, with optional filters."""
    items = [j for j in inference_jobs_db.values() if j["owner_email"] == current_user["email"]]

    if type_:
        items = [j for j in items if j["type"] == type_]
    if model_id:
        items = [j for j in items if j["model_id"] == model_id]
    if status_:
        items = [j for j in items if j["status"] == status_]

    items = sorted(items, key=lambda j: j["created_at"], reverse=True)
    total = len(items)
    items = items[offset: offset + limit]
    return InferenceJobListResponse(total=total, items=items)