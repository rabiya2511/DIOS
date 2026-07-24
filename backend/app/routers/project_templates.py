"""
Templates & Automation router — project templates, create-from-template,
export, import, duplicate.
Matches the Templates & Automation section of the Projects & Workspace
APIs blueprint (6/6).
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.project_templates import (
    TemplateCreateRequest,
    TemplateOut,
    CreateFromTemplateRequest,
    ProjectExportOut,
    ProjectImportRequest,
    ProjectDuplicateRequest,
)
from app.models.user import project_templates_db
from app.routers.projects import projects_db, _get_project_or_404, _require_owner
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1", tags=["Templates & Automation"])


@router.get("/project-templates", response_model=list[TemplateOut])
def list_templates(current_user: dict = Depends(get_current_user)):
    return list(project_templates_db.values())


@router.post("/project-templates", response_model=TemplateOut, status_code=201)
def create_template(
    data: TemplateCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    template_id = str(uuid4())
    template = {
        "id": template_id,
        "name": data.name,
        "description": data.description,
        "creator_email": current_user["email"],
        "created_at": datetime.now(timezone.utc),
    }
    project_templates_db[template_id] = template
    return template


@router.post("/projects/{id}/create-from-template", response_model=dict, status_code=201)
def create_project_from_template(
    id: str,
    data: CreateFromTemplateRequest,
    current_user: dict = Depends(get_current_user),
):
    template = project_templates_db.get(id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    new_id = str(uuid4())
    now = datetime.now(timezone.utc)
    projects_db[new_id] = {
        "id": new_id,
        "name": data.new_name or template["name"],
        "description": template["description"],
        "owner_email": current_user["email"],
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }
    return projects_db[new_id]


@router.post("/projects/{id}/export", response_model=ProjectExportOut)
def export_project(id: str, current_user: dict = Depends(get_current_user)):
    project = _get_project_or_404(id)
    _require_owner(project, current_user["email"])
    return ProjectExportOut(
        id=project["id"],
        name=project["name"],
        description=project["description"],
        owner_email=project["owner_email"],
        status=project["status"],
        exported_at=datetime.now(timezone.utc),
    )


@router.post("/projects/{id}/import", response_model=dict, status_code=201)
def import_project(
    id: str,
    data: ProjectImportRequest,
    current_user: dict = Depends(get_current_user),
):
    # NOTE: {id} here represents the target/parent context for the import;
    # a new project is created from the imported payload.
    new_id = str(uuid4())
    now = datetime.now(timezone.utc)
    projects_db[new_id] = {
        "id": new_id,
        "name": data.name,
        "description": data.description,
        "owner_email": current_user["email"],
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }
    return projects_db[new_id]


@router.post("/projects/{id}/duplicate", response_model=dict, status_code=201)
def duplicate_project(
    id: str,
    data: ProjectDuplicateRequest,
    current_user: dict = Depends(get_current_user),
):
    original = _get_project_or_404(id)
    _require_owner(original, current_user["email"])

    new_id = str(uuid4())
    now = datetime.now(timezone.utc)
    projects_db[new_id] = {
        "id": new_id,
        "name": data.new_name or f"{original['name']} (duplicate)",
        "description": original["description"],
        "owner_email": current_user["email"],
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }
    return projects_db[new_id]