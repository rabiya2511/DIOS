"""
Knowledge Base router — CRUD, archive, restore, clone.
Matches the Knowledge Base section of the Knowledge / RAG APIs
blueprint (8/8). Only the owner can update/delete/archive/restore/clone
their own knowledge base. Mirrors the structure of projects.py.

*** ROUTING NOTE ***
/knowledge/archive, /knowledge/restore, /knowledge/clone are literal
paths under /api/v1/knowledge, the same shape as this router's own
dynamic GET/PATCH/DELETE /knowledge/{id}. All literal routes are
registered BEFORE the /{id} routes below to avoid FastAPI matching
"archive"/"restore"/"clone" as an id value.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.knowledge_base import (
    KnowledgeCreateRequest,
    KnowledgeUpdateRequest,
    KnowledgeOut,
    KnowledgeIdBodyRequest,
    KnowledgeCloneRequest,
)
from app.models.user import knowledge_bases_db
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/knowledge", tags=["Knowledge / RAG: Knowledge Base"])


def _get_kb_or_404(id: str) -> dict:
    kb = knowledge_bases_db.get(id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    return kb


def _require_owner(kb: dict, email: str):
    if kb["owner_email"] != email:
        raise HTTPException(status_code=403, detail="Only the knowledge base owner can perform this action")


@router.get("", response_model=list[KnowledgeOut])
def list_knowledge_bases(current_user: dict = Depends(get_current_user)):
    return [kb for kb in knowledge_bases_db.values() if kb["owner_email"] == current_user["email"]]


@router.post("", response_model=KnowledgeOut, status_code=201)
def create_knowledge_base(
    data: KnowledgeCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    kb_id = str(uuid4())
    now = datetime.now(timezone.utc)
    knowledge_bases_db[kb_id] = {
        "id": kb_id,
        "name": data.name,
        "description": data.description,
        "owner_email": current_user["email"],
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }
    return knowledge_bases_db[kb_id]


# ─── Literal-path routes MUST come before any /{id} routes below ───

@router.post("/archive", response_model=KnowledgeOut)
def archive_knowledge_base(
    data: KnowledgeIdBodyRequest,
    current_user: dict = Depends(get_current_user),
):
    kb = _get_kb_or_404(data.knowledge_id)
    _require_owner(kb, current_user["email"])
    kb["status"] = "archived"
    kb["updated_at"] = datetime.now(timezone.utc)
    return kb


@router.post("/restore", response_model=KnowledgeOut)
def restore_knowledge_base(
    data: KnowledgeIdBodyRequest,
    current_user: dict = Depends(get_current_user),
):
    kb = _get_kb_or_404(data.knowledge_id)
    _require_owner(kb, current_user["email"])
    kb["status"] = "active"
    kb["updated_at"] = datetime.now(timezone.utc)
    return kb


@router.post("/clone", response_model=KnowledgeOut, status_code=201)
def clone_knowledge_base(
    data: KnowledgeCloneRequest,
    current_user: dict = Depends(get_current_user),
):
    original = _get_kb_or_404(data.knowledge_id)
    _require_owner(original, current_user["email"])

    new_id = str(uuid4())
    now = datetime.now(timezone.utc)
    knowledge_bases_db[new_id] = {
        "id": new_id,
        "name": data.new_name or f"{original['name']} (copy)",
        "description": original["description"],
        "owner_email": current_user["email"],
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }
    return knowledge_bases_db[new_id]


# ─── Dynamic /{id} routes come LAST ───

@router.get("/{id}", response_model=KnowledgeOut)
def get_knowledge_base(id: str, current_user: dict = Depends(get_current_user)):
    kb = _get_kb_or_404(id)
    _require_owner(kb, current_user["email"])
    return kb


@router.patch("/{id}", response_model=KnowledgeOut)
def update_knowledge_base(
    id: str,
    data: KnowledgeUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    kb = _get_kb_or_404(id)
    _require_owner(kb, current_user["email"])
    if data.name is not None:
        kb["name"] = data.name
    if data.description is not None:
        kb["description"] = data.description
    kb["updated_at"] = datetime.now(timezone.utc)
    return kb


@router.delete("/{id}", status_code=204)
def delete_knowledge_base(id: str, current_user: dict = Depends(get_current_user)):
    kb = _get_kb_or_404(id)
    _require_owner(kb, current_user["email"])
    del knowledge_bases_db[id]
    return None