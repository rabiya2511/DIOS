"""
Prompt CRUD router — CRUD, archive, restore, clone.
Matches the Prompt CRUD section of the Prompt Management APIs blueprint (8/8).
Only the prompt owner can update/delete/archive/restore/clone their own prompt.

Literal-path routes (/archive, /restore, /clone) MUST come before the
dynamic /{id} routes below — same ordering rule used throughout this codebase.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.prompts import (
    PromptCreateRequest,
    PromptUpdateRequest,
    PromptResponse,
    PromptIdBodyRequest,
    PromptCloneRequest,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/prompts", tags=["Prompt CRUD"])

# id -> {id, title, content, tags, owner_email, status, created_at, updated_at}
prompts_db: dict[str, dict] = {}


def _get_prompt_or_404(id: str) -> dict:
    prompt = prompts_db.get(id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return prompt


def _require_owner(prompt: dict, email: str):
    if prompt["owner_email"] != email:
        raise HTTPException(status_code=403, detail="Only the prompt owner can perform this action")


@router.get("", response_model=list[PromptResponse])
def list_prompts(current_user: dict = Depends(get_current_user)):
    return [p for p in prompts_db.values() if p["owner_email"] == current_user["email"]]


@router.post("", response_model=PromptResponse, status_code=201)
def create_prompt(
    data: PromptCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    prompt_id = str(uuid4())
    now = datetime.now(timezone.utc)
    prompts_db[prompt_id] = {
        "id": prompt_id,
        "title": data.title,
        "content": data.content,
        "tags": data.tags,
        "owner_email": current_user["email"],
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }
    return prompts_db[prompt_id]


# ─── Literal-path routes MUST come before any /{id} routes below ───

@router.post("/archive", response_model=PromptResponse)
def archive_prompt(
    data: PromptIdBodyRequest,
    current_user: dict = Depends(get_current_user),
):
    prompt = _get_prompt_or_404(data.prompt_id)
    _require_owner(prompt, current_user["email"])
    prompt["status"] = "archived"
    prompt["updated_at"] = datetime.now(timezone.utc)
    return prompt


@router.post("/restore", response_model=PromptResponse)
def restore_prompt(
    data: PromptIdBodyRequest,
    current_user: dict = Depends(get_current_user),
):
    prompt = _get_prompt_or_404(data.prompt_id)
    _require_owner(prompt, current_user["email"])
    prompt["status"] = "active"
    prompt["updated_at"] = datetime.now(timezone.utc)
    return prompt


@router.post("/clone", response_model=PromptResponse, status_code=201)
def clone_prompt(
    data: PromptCloneRequest,
    current_user: dict = Depends(get_current_user),
):
    original = _get_prompt_or_404(data.prompt_id)
    _require_owner(original, current_user["email"])

    new_id = str(uuid4())
    now = datetime.now(timezone.utc)
    prompts_db[new_id] = {
        "id": new_id,
        "title": data.new_title or f"{original['title']} (copy)",
        "content": original["content"],
        "tags": list(original["tags"]),
        "owner_email": current_user["email"],
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }
    return prompts_db[new_id]


# ─── Dynamic /{id} routes come LAST ───

@router.get("/{id}", response_model=PromptResponse)
def get_prompt(id: str, current_user: dict = Depends(get_current_user)):
    prompt = _get_prompt_or_404(id)
    _require_owner(prompt, current_user["email"])
    return prompt


@router.patch("/{id}", response_model=PromptResponse)
def update_prompt(
    id: str,
    data: PromptUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    prompt = _get_prompt_or_404(id)
    _require_owner(prompt, current_user["email"])
    if data.title is not None:
        prompt["title"] = data.title
    if data.content is not None:
        prompt["content"] = data.content
    if data.tags is not None:
        prompt["tags"] = data.tags
    prompt["updated_at"] = datetime.now(timezone.utc)
    return prompt


@router.delete("/{id}", status_code=204)
def delete_prompt(id: str, current_user: dict = Depends(get_current_user)):
    prompt = _get_prompt_or_404(id)
    _require_owner(prompt, current_user["email"])
    del prompts_db[id]
    return None