"""
Project Management router — CRUD, archive, restore, clone.
Matches the Project Management section of the Projects & Workspace APIs
blueprint (8/8).
Only the project owner can update/delete/archive/restore/clone their own
project. Mirrors the structure of fileslifecycle.py.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.projects import (
    ProjectCreateRequest,
    ProjectUpdateRequest,
    ProjectResponse,
    ProjectIdBodyRequest,
    ProjectCloneRequest,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/projects", tags=["Project Management"])

# id -> {id, name, description, owner_email, status, created_at, updated_at}
projects_db: dict[str, dict] = {}


def _get_project_or_404(id: str) -> dict:
    project = projects_db.get(id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _require_owner(project: dict, email: str):
    if project["owner_email"] != email:
        raise HTTPException(status_code=403, detail="Only the project owner can perform this action")


@router.get("", response_model=list[ProjectResponse])
def list_projects(current_user: dict = Depends(get_current_user)):
    return [
        project
        for project in projects_db.values()
        if project["owner_email"] == current_user["email"]
    ]


@router.post("", response_model=ProjectResponse, status_code=201)
def create_project(
    data: ProjectCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    project_id = str(uuid4())
    now = datetime.now(timezone.utc)
    projects_db[project_id] = {
        "id": project_id,
        "name": data.name,
        "description": data.description,
        "owner_email": current_user["email"],
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }
    return projects_db[project_id]


# ─── Literal-path routes MUST come before any /{id} routes below ───

@router.post("/archive", response_model=ProjectResponse)
def archive_project(
    data: ProjectIdBodyRequest,
    current_user: dict = Depends(get_current_user),
):
    project = _get_project_or_404(data.project_id)
    _require_owner(project, current_user["email"])
    project["status"] = "archived"
    project["updated_at"] = datetime.now(timezone.utc)
    return project


@router.post("/restore", response_model=ProjectResponse)
def restore_project(
    data: ProjectIdBodyRequest,
    current_user: dict = Depends(get_current_user),
):
    project = _get_project_or_404(data.project_id)
    _require_owner(project, current_user["email"])
    project["status"] = "active"
    project["updated_at"] = datetime.now(timezone.utc)
    return project


@router.post("/clone", response_model=ProjectResponse, status_code=201)
def clone_project(
    data: ProjectCloneRequest,
    current_user: dict = Depends(get_current_user),
):
    original = _get_project_or_404(data.project_id)
    _require_owner(original, current_user["email"])

    new_id = str(uuid4())
    now = datetime.now(timezone.utc)
    projects_db[new_id] = {
        "id": new_id,
        "name": data.new_name or f"{original['name']} (copy)",
        "description": original["description"],
        "owner_email": current_user["email"],
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }
    return projects_db[new_id]


# ─── Dynamic /{id} routes come LAST ───

@router.get("/{id}", response_model=ProjectResponse)
def get_project(id: str, current_user: dict = Depends(get_current_user)):
    project = _get_project_or_404(id)
    _require_owner(project, current_user["email"])
    return project


@router.patch("/{id}", response_model=ProjectResponse)
def update_project(
    id: str,
    data: ProjectUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    project = _get_project_or_404(id)
    _require_owner(project, current_user["email"])
    if data.name is not None:
        project["name"] = data.name
    if data.description is not None:
        project["description"] = data.description
    project["updated_at"] = datetime.now(timezone.utc)
    return project


@router.delete("/{id}", status_code=204)
def delete_project(id: str, current_user: dict = Depends(get_current_user)):
    project = _get_project_or_404(id)
    _require_owner(project, current_user["email"])
    del projects_db[id]
    return None