"""
Project Resources router — files, datasets, models attached to a project.
Matches the Project Resources section of the Projects & Workspace APIs
blueprint (6/6).

ASSUMPTIONS:
- These are lightweight, project-scoped metadata records only (name, size,
  framework, etc.) — NOT the same as the global File & Storage domain's
  files_db (fileslifecycle.py). A project "file" here doesn't create or
  reference a real files_db entry. If you want project files to actually
  BE files_db entries, that's a follow-up integration, not done here.
- Any member of the project (any role — owner/admin/member) can view and
  add resources; there's no extra permission tier beyond "is a member",
  reusing _get_members from project_members.py for that check.
- No update/delete endpoints exist for resources in this blueprint section
  — only GET (list) and POST (add) for each of files/datasets/models.

IMPORTANT: Shares the /api/v1/projects prefix with projects.router and
project_members.router. All routes here are 2-segment paths
(/{project_id}/files, /{project_id}/datasets, /{project_id}/models), same
shape class as project_members.py's /{project_id}/members — no collision
with projects.router's single-segment /{id}, /archive, /restore, /clone,
and no collision with project_members.py's 3+ segment member routes
either. No route-ordering fix needed.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.project_resources import (
    ProjectFileCreateRequest,
    ProjectFileOut,
    ProjectDatasetCreateRequest,
    ProjectDatasetOut,
    ProjectModelCreateRequest,
    ProjectModelOut,
)
from app.routers.projects import _get_project_or_404
from app.routers.project_members import _get_members
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/projects", tags=["Project Resources"])

# project_id -> list of resource dicts
project_files_db: dict[str, list[dict]] = {}
project_datasets_db: dict[str, list[dict]] = {}
project_models_db: dict[str, list[dict]] = {}


def _require_member(project_id: str, email: str):
    members = _get_members(project_id)
    if email not in members:
        raise HTTPException(status_code=403, detail="Not a member of this project")


@router.get("/{project_id}/files", response_model=list[ProjectFileOut])
def list_project_files(project_id: str, current_user: dict = Depends(get_current_user)):
    _get_project_or_404(project_id)
    _require_member(project_id, current_user["email"])
    return project_files_db.get(project_id, [])


@router.post("/{project_id}/files", response_model=ProjectFileOut, status_code=201)
def add_project_file(
    project_id: str,
    data: ProjectFileCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    _get_project_or_404(project_id)
    _require_member(project_id, current_user["email"])
    record = {
        "id": str(uuid4()),
        "project_id": project_id,
        "name": data.name,
        "size_bytes": data.size_bytes,
        "mime_type": data.mime_type,
        "added_by": current_user["email"],
        "created_at": datetime.now(timezone.utc),
    }
    project_files_db.setdefault(project_id, []).append(record)
    return record


@router.get("/{project_id}/datasets", response_model=list[ProjectDatasetOut])
def list_project_datasets(project_id: str, current_user: dict = Depends(get_current_user)):
    _get_project_or_404(project_id)
    _require_member(project_id, current_user["email"])
    return project_datasets_db.get(project_id, [])


@router.post("/{project_id}/datasets", response_model=ProjectDatasetOut, status_code=201)
def add_project_dataset(
    project_id: str,
    data: ProjectDatasetCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    _get_project_or_404(project_id)
    _require_member(project_id, current_user["email"])
    record = {
        "id": str(uuid4()),
        "project_id": project_id,
        "name": data.name,
        "description": data.description,
        "row_count": data.row_count,
        "added_by": current_user["email"],
        "created_at": datetime.now(timezone.utc),
    }
    project_datasets_db.setdefault(project_id, []).append(record)
    return record


@router.get("/{project_id}/models", response_model=list[ProjectModelOut])
def list_project_models(project_id: str, current_user: dict = Depends(get_current_user)):
    _get_project_or_404(project_id)
    _require_member(project_id, current_user["email"])
    return project_models_db.get(project_id, [])


@router.post("/{project_id}/models", response_model=ProjectModelOut, status_code=201)
def add_project_model(
    project_id: str,
    data: ProjectModelCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    _get_project_or_404(project_id)
    _require_member(project_id, current_user["email"])
    record = {
        "id": str(uuid4()),
        "project_id": project_id,
        "name": data.name,
        "framework": data.framework,
        "version": data.version,
        "added_by": current_user["email"],
        "created_at": datetime.now(timezone.utc),
    }
    project_models_db.setdefault(project_id, []).append(record)
    return record