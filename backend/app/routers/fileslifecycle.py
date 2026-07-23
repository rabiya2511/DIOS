"""
File Lifecycle router — CRUD, archive, restore, clone.
Matches the File Lifecycle section of the File & Storage APIs blueprint (8/8).
Only the file owner can update/delete/archive/restore/clone their own file.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.fileslifecycle import (
    FileCreateRequest,
    FileUpdateRequest,
    FileResponse,
    FileIdBodyRequest,
    FileCloneRequest,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/files", tags=["File Lifecycle"])

# id -> {id, name, folder_id, size_bytes, mime_type, owner_email, status, created_at, updated_at}
files_db: dict[str, dict] = {}


def _get_file_or_404(id: str) -> dict:
    file = files_db.get(id)
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    return file


def _require_owner(file: dict, email: str):
    if file["owner_email"] != email:
        raise HTTPException(status_code=403, detail="Only the file owner can perform this action")


@router.get("", response_model=list[FileResponse])
def list_files(current_user: dict = Depends(get_current_user)):
    return [
        file
        for file in files_db.values()
        if file["owner_email"] == current_user["email"]
    ]


@router.post("", response_model=FileResponse, status_code=201)
def create_file(
    data: FileCreateRequest,
    current_user: dict = Depends(get_current_user),
):
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


# ─── Literal-path routes MUST come before any /{id} routes below ───

@router.post("/archive", response_model=FileResponse)
def archive_file(
    data: FileIdBodyRequest,
    current_user: dict = Depends(get_current_user),
):
    file = _get_file_or_404(data.file_id)
    _require_owner(file, current_user["email"])
    file["status"] = "archived"
    file["updated_at"] = datetime.now(timezone.utc)
    return file


@router.post("/restore", response_model=FileResponse)
def restore_file(
    data: FileIdBodyRequest,
    current_user: dict = Depends(get_current_user),
):
    file = _get_file_or_404(data.file_id)
    _require_owner(file, current_user["email"])
    file["status"] = "active"
    file["updated_at"] = datetime.now(timezone.utc)
    return file


@router.post("/clone", response_model=FileResponse, status_code=201)
def clone_file(
    data: FileCloneRequest,
    current_user: dict = Depends(get_current_user),
):
    original = _get_file_or_404(data.file_id)
    _require_owner(original, current_user["email"])

    new_id = str(uuid4())
    now = datetime.now(timezone.utc)
    files_db[new_id] = {
        "id": new_id,
        "name": data.new_name or f"{original['name']} (copy)",
        "folder_id": original["folder_id"],
        "size_bytes": original["size_bytes"],
        "mime_type": original["mime_type"],
        "owner_email": current_user["email"],
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }
    return files_db[new_id]


# ─── Dynamic /{id} routes come LAST ───

@router.get("/{id}", response_model=FileResponse)
def get_file(id: str, current_user: dict = Depends(get_current_user)):
    file = _get_file_or_404(id)
    _require_owner(file, current_user["email"])
    return file


@router.patch("/{id}", response_model=FileResponse)
def update_file(
    id: str,
    data: FileUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    file = _get_file_or_404(id)
    _require_owner(file, current_user["email"])
    if data.name is not None:
        file["name"] = data.name
    if data.folder_id is not None:
        file["folder_id"] = data.folder_id
    file["updated_at"] = datetime.now(timezone.utc)
    return file


@router.delete("/{id}", status_code=204)
def delete_file(id: str, current_user: dict = Depends(get_current_user)):
    file = _get_file_or_404(id)
    _require_owner(file, current_user["email"])
    del files_db[id]
    return None