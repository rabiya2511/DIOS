"""
Upload & Download router — direct upload, chunked upload, download,
signed URLs, copy, move, rename.
Matches the Upload & Download section of the File & Storage APIs blueprint (8/8).

IMPORTANT: This router shares the /api/v1/files prefix with the File
Lifecycle router (fileslifecycle.py) and reuses its in-memory files_db.
Because File Lifecycle has a dynamic GET /files/{id} route, THIS router
must be included in main.py BEFORE fileslifecycle.router, so that literal
paths like /files/download are matched before the {id} pattern.
"""

import base64
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query

from app.schemas.uploaddownload import (
    FileUploadRequest,
    ChunkUploadRequest,
    ChunkUploadResponse,
    UploadCompleteRequest,
    UploadedFileResponse,
    SignedUrlRequest,
    SignedUrlResponse,
    FileCopyRequest,
    FileMoveRequest,
    FileRenameRequest,
)
from app.core.security import get_current_user
from app.routers.fileslifecycle import files_db, _get_file_or_404, _require_owner

router = APIRouter(prefix="/api/v1/files", tags=["Upload & Download"])

# upload_id -> {owner_email, name, folder_id, mime_type, total_chunks, chunks: {index: bytes}}
uploads_db: dict[str, dict] = {}


@router.post("/upload", response_model=UploadedFileResponse, status_code=201)
def upload_file(
    data: FileUploadRequest,
    current_user: dict = Depends(get_current_user),
):
    """Direct (non-chunked) upload — creates a file record immediately."""
    file_id = str(uuid4())
    now = datetime.now(timezone.utc)
    files_db[file_id] = {
        "id": file_id,
        "name": data.name,
        "folder_id": data.folder_id,
        "size_bytes": data.size_bytes or 0,
        "mime_type": data.mime_type,
        "owner_email": current_user["email"],
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }
    return files_db[file_id]


@router.post("/upload/chunk", response_model=ChunkUploadResponse)
def upload_chunk(
    data: ChunkUploadRequest,
    current_user: dict = Depends(get_current_user),
):
    """Receive one chunk of a larger upload, keyed by upload_id."""
    upload = uploads_db.setdefault(
        data.upload_id,
        {
            "owner_email": current_user["email"],
            "total_chunks": data.total_chunks,
            "chunks": {},
        },
    )
    if upload["owner_email"] != current_user["email"]:
        raise HTTPException(status_code=403, detail="Not the owner of this upload session")

    upload["chunks"][data.chunk_index] = base64.b64decode(data.data_base64)
    return ChunkUploadResponse(
        upload_id=data.upload_id, chunk_index=data.chunk_index, received=True
    )


@router.post("/upload/complete", response_model=UploadedFileResponse, status_code=201)
def complete_upload(
    data: UploadCompleteRequest,
    current_user: dict = Depends(get_current_user),
):
    """Assemble received chunks into a final file record."""
    upload = uploads_db.get(data.upload_id)
    if not upload:
        raise HTTPException(status_code=404, detail="Upload session not found")
    if upload["owner_email"] != current_user["email"]:
        raise HTTPException(status_code=403, detail="Not the owner of this upload session")
    if len(upload["chunks"]) != upload["total_chunks"]:
        raise HTTPException(
            status_code=400,
            detail=f"Expected {upload['total_chunks']} chunks, received {len(upload['chunks'])}",
        )

    assembled = b"".join(upload["chunks"][i] for i in sorted(upload["chunks"]))
    file_id = str(uuid4())
    now = datetime.now(timezone.utc)
    files_db[file_id] = {
        "id": file_id,
        "name": upload.get("name") or f"upload-{file_id}",
        "folder_id": upload.get("folder_id"),
        "size_bytes": len(assembled),
        "mime_type": upload.get("mime_type"),
        "owner_email": current_user["email"],
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }
    del uploads_db[data.upload_id]
    return files_db[file_id]


@router.get("/download")
def download_file(
    file_id: str = Query(...),
    current_user: dict = Depends(get_current_user),
):
    """Return file metadata as a stand-in for streaming actual bytes."""
    file = _get_file_or_404(file_id)
    _require_owner(file, current_user["email"])
    return {
        "id": file["id"],
        "name": file["name"],
        "mime_type": file["mime_type"],
        "size_bytes": file["size_bytes"],
        "note": "Placeholder response — real binary streaming requires actual storage backend.",
    }


@router.post("/download/signed-url", response_model=SignedUrlResponse)
def get_signed_download_url(
    data: SignedUrlRequest,
    current_user: dict = Depends(get_current_user),
):
    file = _get_file_or_404(data.file_id)
    _require_owner(file, current_user["email"])
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=data.expires_in_seconds or 3600)
    fake_url = f"https://storage.example.com/signed/{file['id']}?exp={int(expires_at.timestamp())}"
    return SignedUrlResponse(file_id=file["id"], url=fake_url, expires_at=expires_at)


@router.post("/copy", response_model=UploadedFileResponse, status_code=201)
def copy_file(
    data: FileCopyRequest,
    current_user: dict = Depends(get_current_user),
):
    original = _get_file_or_404(data.file_id)
    _require_owner(original, current_user["email"])

    new_id = str(uuid4())
    now = datetime.now(timezone.utc)
    files_db[new_id] = {
        "id": new_id,
        "name": original["name"],
        "folder_id": data.destination_folder_id or original["folder_id"],
        "size_bytes": original["size_bytes"],
        "mime_type": original["mime_type"],
        "owner_email": current_user["email"],
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }
    return files_db[new_id]


@router.post("/move", response_model=UploadedFileResponse)
def move_file(
    data: FileMoveRequest,
    current_user: dict = Depends(get_current_user),
):
    file = _get_file_or_404(data.file_id)
    _require_owner(file, current_user["email"])
    file["folder_id"] = data.destination_folder_id
    file["updated_at"] = datetime.now(timezone.utc)
    return file


@router.post("/rename", response_model=UploadedFileResponse)
def rename_file(
    data: FileRenameRequest,
    current_user: dict = Depends(get_current_user),
):
    file = _get_file_or_404(data.file_id)
    _require_owner(file, current_user["email"])
    file["name"] = data.new_name
    file["updated_at"] = datetime.now(timezone.utc)
    return file