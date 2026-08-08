"""
Router for the Audio Upload & Storage group of the Audio Services
APIs blueprint.
  POST   /api/v1/audio/upload
  GET    /api/v1/audio
  GET    /api/v1/audio/{id}
  PATCH  /api/v1/audio/{id}
  DELETE /api/v1/audio/{id}
  POST   /api/v1/audio/bulk-upload

Only the audio owner can get/update/delete their own file — same
ownership model as conversations.py / image_storage.py. Uses a local
in-memory dict (same pattern as conversations_db).

*** STORAGE NOTE ***
Does NOT persist uploaded bytes anywhere permanent beyond local disk —
no blob storage (S3/GCS/etc.) is wired up, and no real audio decoding
happens, so `duration_seconds` is simulated, not measured. Each upload
reads the file just to record filename/content_type/size_bytes and
returns a simulated `url`. Wire up real storage + audio metadata
extraction (e.g. via ffprobe/mutagen) before relying on this for
anything beyond API-shape testing. Requires `python-multipart` for
UploadFile/Form parsing.

*** FILE TYPE VALIDATION ***
Uploads are restricted to the content types in ALLOWED_TYPES below.
Anything else is rejected with a 400.
"""

import os
import shutil
from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from app.schemas.audio_storage import (
    AudioUpdateRequest,
    AudioOut,
    AudioListResponse,
    AudioBulkUploadResponse,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/audio", tags=["Audio Upload"])

# id -> {id, owner_email, filename, content_type, size_bytes, duration_seconds,
#        url, tags, metadata, created_at, updated_at}
audio_files_db: dict[str, dict] = {}

UPLOAD_DIR = "app/uploads/audio"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_TYPES = {
    "audio/mpeg",
    "audio/mp3",
    "audio/wav",
    "audio/x-wav",
    "audio/mp4",
    "audio/x-m4a",
    "audio/aac",
    "audio/ogg",
    "audio/flac",
}


def _get_audio_or_404(id: str) -> dict:
    audio = audio_files_db.get(id)
    if not audio:
        raise HTTPException(status_code=404, detail="Audio file not found")
    return audio


def _require_owner(audio: dict, email: str):
    if audio["owner_email"] != email:
        raise HTTPException(status_code=403, detail="Only the audio owner can perform this action")


async def _register_upload(file: UploadFile, owner_email: str, tags: list[str]) -> dict:
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Only audio files are allowed.")

    extension = os.path.splitext(file.filename)[1]
    stored_filename = f"{uuid4()}{extension}"
    filepath = os.path.join(UPLOAD_DIR, stored_filename)

    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    size = os.path.getsize(filepath)
    audio_id = stored_filename.split(".")[0]
    now = datetime.now(timezone.utc)

    audio = {
        "id": audio_id,
        "owner_email": owner_email,
        "filename": file.filename,
        "content_type": file.content_type,
        "size_bytes": size,
        "duration_seconds": 0.0,  # STUB: not measured, no audio decoding wired up
        "url": f"/api/v1/audio/{audio_id}/file",  # simulated — no real serving route yet
        "tags": tags,
        "metadata": {},
        "created_at": now,
        "updated_at": now,
    }
    audio_files_db[audio_id] = audio
    return audio


# ---------------------------------------------------------------------------
# POST /api/v1/audio/upload
# ---------------------------------------------------------------------------
@router.post("/upload", response_model=AudioOut, status_code=201)
async def upload_audio(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    return await _register_upload(file, current_user["email"], [])


# ---------------------------------------------------------------------------
# POST /api/v1/audio/bulk-upload
# ---------------------------------------------------------------------------
@router.post("/bulk-upload", response_model=AudioBulkUploadResponse, status_code=201)
async def bulk_upload_audio(
    files: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Upload multiple audio files in a single request."""
    items = []
    for file in files:
        audio = await _register_upload(file, current_user["email"], [])
        items.append(audio)
    return AudioBulkUploadResponse(total_uploaded=len(items), items=items)


# ---------------------------------------------------------------------------
# GET /api/v1/audio
# ---------------------------------------------------------------------------
@router.get("", response_model=AudioListResponse)
def list_audio(
    tag: Optional[str] = Query(None, description="Filter by tag"),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    """List the caller's uploaded audio files."""
    items = [a for a in audio_files_db.values() if a["owner_email"] == current_user["email"]]

    if tag:
        items = [a for a in items if tag in a["tags"]]

    items = sorted(items, key=lambda a: a["created_at"], reverse=True)
    total = len(items)
    items = items[offset: offset + limit]
    return AudioListResponse(total=total, items=items)


# ---------------------------------------------------------------------------
# GET /api/v1/audio/{id}
# ---------------------------------------------------------------------------
@router.get("/{id}", response_model=AudioOut)
def get_audio(id: str, current_user: dict = Depends(get_current_user)):
    """Get a single audio file's metadata."""
    audio = _get_audio_or_404(id)
    _require_owner(audio, current_user["email"])
    return audio


# ---------------------------------------------------------------------------
# PATCH /api/v1/audio/{id}
# ---------------------------------------------------------------------------
@router.patch("/{id}", response_model=AudioOut)
def update_audio(
    id: str,
    data: AudioUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    """Update an audio file's filename, tags, and/or metadata."""
    audio = _get_audio_or_404(id)
    _require_owner(audio, current_user["email"])

    update_data = data.model_dump(exclude_unset=True)
    audio.update(update_data)
    audio["updated_at"] = datetime.now(timezone.utc)
    return audio


# ---------------------------------------------------------------------------
# DELETE /api/v1/audio/{id}
# ---------------------------------------------------------------------------
@router.delete("/{id}", status_code=204)
def delete_audio(id: str, current_user: dict = Depends(get_current_user)):
    """Delete an audio file."""
    audio = _get_audio_or_404(id)
    _require_owner(audio, current_user["email"])
    del audio_files_db[id]
    return None