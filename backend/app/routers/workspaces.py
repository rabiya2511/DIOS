"""
Workspace router — CRUD, switch, recent, archive, restore.
Matches the Workspace section of the User Management blueprint (8/8).
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.workspaces import (
    WorkspaceCreateRequest,
    WorkspaceUpdateRequest,
    WorkspaceOut,
    WorkspaceSwitchRequest,
    WorkspaceSwitchResponse,
    WorkspaceArchiveRequest,
)
from app.models.user import workspaces_db, current_workspace_db, recent_workspaces_db
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/workspaces", tags=["Workspace"])

RECENT_LIMIT = 5


def _get_owned_workspace(workspace_id: str, current_user: dict) -> dict:
    ws = workspaces_db.get(workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if ws["owner_email"] != current_user["email"]:
        raise HTTPException(status_code=403, detail="Only the workspace owner can perform this action")
    return ws


@router.get("", response_model=list[WorkspaceOut])
def list_workspaces(current_user: dict = Depends(get_current_user)):
    email = current_user["email"]
    return [ws for ws in workspaces_db.values() if ws["owner_email"] == email]


@router.post("", response_model=WorkspaceOut, status_code=201)
def create_workspace(
    data: WorkspaceCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    workspace_id = str(uuid4())
    ws = {
        "id": workspace_id,
        "name": data.name,
        "owner_email": current_user["email"],
        "status": "active",
        "created_at": datetime.now(timezone.utc),
    }
    workspaces_db[workspace_id] = ws
    return ws


# ─── Fixed literal-path routes before /{workspace_id} routes ───

@router.post("/switch", response_model=WorkspaceSwitchResponse)
def switch_workspace(
    data: WorkspaceSwitchRequest,
    current_user: dict = Depends(get_current_user),
):
    ws = workspaces_db.get(data.workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if ws["owner_email"] != current_user["email"]:
        raise HTTPException(status_code=403, detail="You do not have access to this workspace")

    email = current_user["email"]
    current_workspace_db[email] = data.workspace_id

    recent = recent_workspaces_db.setdefault(email, [])
    if data.workspace_id in recent:
        recent.remove(data.workspace_id)
    recent.insert(0, data.workspace_id)
    del recent[RECENT_LIMIT:]

    return WorkspaceSwitchResponse(current_workspace_id=data.workspace_id)


@router.get("/recent", response_model=list[WorkspaceOut])
def get_recent_workspaces(current_user: dict = Depends(get_current_user)):
    email = current_user["email"]
    recent_ids = recent_workspaces_db.get(email, [])
    return [workspaces_db[wid] for wid in recent_ids if wid in workspaces_db]


@router.post("/archive", response_model=WorkspaceOut)
def archive_workspace(
    data: WorkspaceArchiveRequest,
    current_user: dict = Depends(get_current_user),
):
    ws = _get_owned_workspace(data.workspace_id, current_user)
    ws["status"] = "archived"
    return ws


@router.post("/restore", response_model=WorkspaceOut)
def restore_workspace(
    data: WorkspaceArchiveRequest,
    current_user: dict = Depends(get_current_user),
):
    ws = _get_owned_workspace(data.workspace_id, current_user)
    ws["status"] = "active"
    return ws


# ─── Dynamic /{workspace_id} routes LAST ───

@router.patch("/{workspace_id}", response_model=WorkspaceOut)
def update_workspace(
    workspace_id: str,
    data: WorkspaceUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    ws = _get_owned_workspace(workspace_id, current_user)
    if data.name is not None:
        ws["name"] = data.name
    return ws


@router.delete("/{workspace_id}", status_code=204)
def delete_workspace(
    workspace_id: str,
    current_user: dict = Depends(get_current_user),
):
    _get_owned_workspace(workspace_id, current_user)
    del workspaces_db[workspace_id]
    return None