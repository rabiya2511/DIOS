"""
Folders router — CRUD, share, tree, archive, restore.
Matches the Folders section of the File & Storage APIs blueprint (8/8).
Only the folder owner can update/delete/share/archive/restore it.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.folders import (
    FolderCreateRequest,
    FolderUpdateRequest,
    FolderResponse,
    FolderIdBodyRequest,
    FolderShareRequest,
    FolderShareResponse,
    FolderTreeNode,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/folders", tags=["Folders"])

# id -> {id, name, parent_folder_id, owner_email, status, created_at, updated_at}
folders_db: dict[str, dict] = {}

# folder_id -> set of emails the folder is shared with
folder_shares_db: dict[str, set] = {}


def _get_folder_or_404(id: str) -> dict:
    folder = folders_db.get(id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    return folder


def _require_owner(folder: dict, email: str):
    if folder["owner_email"] != email:
        raise HTTPException(status_code=403, detail="Only the folder owner can perform this action")


@router.get("", response_model=list[FolderResponse])
def list_folders(current_user: dict = Depends(get_current_user)):
    return [
        folder
        for folder in folders_db.values()
        if folder["owner_email"] == current_user["email"]
    ]


@router.post("", response_model=FolderResponse, status_code=201)
def create_folder(
    data: FolderCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    folder_id = str(uuid4())
    now = datetime.now(timezone.utc)
    folders_db[folder_id] = {
        "id": folder_id,
        "name": data.name,
        "parent_folder_id": data.parent_folder_id,
        "owner_email": current_user["email"],
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }
    folder_shares_db[folder_id] = set()
    return folders_db[folder_id]


# ─── Literal-path routes MUST come before any /{id} routes below ───

@router.post("/share", response_model=FolderShareResponse, status_code=201)
def share_folder(
    data: FolderShareRequest,
    current_user: dict = Depends(get_current_user),
):
    folder = _get_folder_or_404(data.folder_id)
    _require_owner(folder, current_user["email"])
    folder_shares_db.setdefault(data.folder_id, set()).add(data.email)
    return FolderShareResponse(
        folder_id=data.folder_id,
        shared_with_email=data.email,
        shared_at=datetime.now(timezone.utc),
    )


@router.get("/tree", response_model=list[FolderTreeNode])
def get_folder_tree(current_user: dict = Depends(get_current_user)):
    """Build a nested tree of the current user's folders."""
    owned = [f for f in folders_db.values() if f["owner_email"] == current_user["email"]]

    def build_children(parent_id: str | None) -> list[FolderTreeNode]:
        return [
            FolderTreeNode(
                id=f["id"],
                name=f["name"],
                children=build_children(f["id"]),
            )
            for f in owned
            if f["parent_folder_id"] == parent_id
        ]

    return build_children(None)


@router.post("/archive", response_model=FolderResponse)
def archive_folder(
    data: FolderIdBodyRequest,
    current_user: dict = Depends(get_current_user),
):
    folder = _get_folder_or_404(data.folder_id)
    _require_owner(folder, current_user["email"])
    folder["status"] = "archived"
    folder["updated_at"] = datetime.now(timezone.utc)
    return folder


@router.post("/restore", response_model=FolderResponse)
def restore_folder(
    data: FolderIdBodyRequest,
    current_user: dict = Depends(get_current_user),
):
    folder = _get_folder_or_404(data.folder_id)
    _require_owner(folder, current_user["email"])
    folder["status"] = "active"
    folder["updated_at"] = datetime.now(timezone.utc)
    return folder


# ─── Dynamic /{id} routes come LAST ───

@router.patch("/{id}", response_model=FolderResponse)
def update_folder(
    id: str,
    data: FolderUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    folder = _get_folder_or_404(id)
    _require_owner(folder, current_user["email"])
    if data.name is not None:
        folder["name"] = data.name
    if data.parent_folder_id is not None:
        folder["parent_folder_id"] = data.parent_folder_id
    folder["updated_at"] = datetime.now(timezone.utc)
    return folder


@router.delete("/{id}", status_code=204)
def delete_folder(id: str, current_user: dict = Depends(get_current_user)):
    folder = _get_folder_or_404(id)
    _require_owner(folder, current_user["email"])
    del folders_db[id]
    folder_shares_db.pop(id, None)
    return None