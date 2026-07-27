"""
Templates router — CRUD, import, export, duplicate.
Matches the Templates section of the Prompt Management APIs blueprint (8/8).
Only the template owner can update/delete/duplicate their own template.

Literal-path routes (/import, /export, /duplicate) MUST come before the
dynamic /{id} routes below — same ordering rule used throughout this codebase.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.templates import (
    TemplateCreateRequest,
    TemplateUpdateRequest,
    TemplateResponse,
    TemplateImportRequest,
    TemplateImportResponse,
    TemplateDuplicateRequest,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/prompt-templates", tags=["Templates"])

# id -> {id, name, content, variables, owner_email, created_at, updated_at}
templates_db: dict[str, dict] = {}


def _get_template_or_404(id: str) -> dict:
    template = templates_db.get(id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


def _require_owner(template: dict, email: str):
    if template["owner_email"] != email:
        raise HTTPException(status_code=403, detail="Only the template owner can perform this action")


@router.get("", response_model=list[TemplateResponse])
def list_templates(current_user: dict = Depends(get_current_user)):
    return [t for t in templates_db.values() if t["owner_email"] == current_user["email"]]


@router.post("", response_model=TemplateResponse, status_code=201)
def create_template(
    data: TemplateCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    template_id = str(uuid4())
    now = datetime.now(timezone.utc)
    templates_db[template_id] = {
        "id": template_id,
        "name": data.name,
        "content": data.content,
        "variables": data.variables,
        "owner_email": current_user["email"],
        "created_at": now,
        "updated_at": now,
    }
    return templates_db[template_id]


# ─── Literal-path routes MUST come before any /{id} routes below ───

@router.post("/import", response_model=TemplateImportResponse, status_code=201)
def import_templates(
    data: TemplateImportRequest,
    current_user: dict = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)
    for item in data.templates:
        template_id = str(uuid4())
        templates_db[template_id] = {
            "id": template_id,
            "name": item.name,
            "content": item.content,
            "variables": item.variables,
            "owner_email": current_user["email"],
            "created_at": now,
            "updated_at": now,
        }
    return TemplateImportResponse(imported_count=len(data.templates))


@router.post("/export", response_model=list[TemplateResponse])
def export_templates(current_user: dict = Depends(get_current_user)):
    return [t for t in templates_db.values() if t["owner_email"] == current_user["email"]]


@router.post("/duplicate", response_model=TemplateResponse, status_code=201)
def duplicate_template(
    data: TemplateDuplicateRequest,
    current_user: dict = Depends(get_current_user),
):
    original = _get_template_or_404(data.template_id)
    _require_owner(original, current_user["email"])

    new_id = str(uuid4())
    now = datetime.now(timezone.utc)
    templates_db[new_id] = {
        "id": new_id,
        "name": data.new_name or f"{original['name']} (copy)",
        "content": original["content"],
        "variables": list(original["variables"]),
        "owner_email": current_user["email"],
        "created_at": now,
        "updated_at": now,
    }
    return templates_db[new_id]


# ─── Dynamic /{id} routes come LAST ───

@router.get("/{id}", response_model=TemplateResponse)
def get_template(id: str, current_user: dict = Depends(get_current_user)):
    template = _get_template_or_404(id)
    _require_owner(template, current_user["email"])
    return template


@router.patch("/{id}", response_model=TemplateResponse)
def update_template(
    id: str,
    data: TemplateUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    template = _get_template_or_404(id)
    _require_owner(template, current_user["email"])
    if data.name is not None:
        template["name"] = data.name
    if data.content is not None:
        template["content"] = data.content
    if data.variables is not None:
        template["variables"] = data.variables
    template["updated_at"] = datetime.now(timezone.utc)
    return template


@router.delete("/{id}", status_code=204)
def delete_template(id: str, current_user: dict = Depends(get_current_user)):
    template = _get_template_or_404(id)
    _require_owner(template, current_user["email"])
    del templates_db[id]
    return None