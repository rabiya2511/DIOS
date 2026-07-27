"""
System & Developer Prompts router — CRUD for both resource types.
Matches the System & Developer Prompts section of the Prompt Management
APIs blueprint (8/8).

Two independent resources (system prompts and developer prompts) live in
this one router since the blueprint groups them as a single domain.
No prefix is set at the router level — each route specifies its full
path (/system-prompts/... or /developer-prompts/...) so both resource
shapes coexist cleanly under one file.

Only the owner can update/delete their own prompt (of either type).
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.system_developer_prompts import (
    SystemPromptCreateRequest,
    SystemPromptUpdateRequest,
    SystemPromptResponse,
    DeveloperPromptCreateRequest,
    DeveloperPromptUpdateRequest,
    DeveloperPromptResponse,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1", tags=["System & Developer Prompts"])

# id -> {id, content, description, owner_email, created_at, updated_at}
system_prompts_db: dict[str, dict] = {}
developer_prompts_db: dict[str, dict] = {}


def _get_or_404(db: dict, id: str, label: str) -> dict:
    item = db.get(id)
    if not item:
        raise HTTPException(status_code=404, detail=f"{label} not found")
    return item


def _require_owner(item: dict, email: str, label: str):
    if item["owner_email"] != email:
        raise HTTPException(status_code=403, detail=f"Only the {label} owner can perform this action")


# ─── System Prompts ───

@router.get("/system-prompts", response_model=list[SystemPromptResponse])
def list_system_prompts(current_user: dict = Depends(get_current_user)):
    return [p for p in system_prompts_db.values() if p["owner_email"] == current_user["email"]]


@router.post("/system-prompts", response_model=SystemPromptResponse, status_code=201)
def create_system_prompt(
    data: SystemPromptCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    prompt_id = str(uuid4())
    now = datetime.now(timezone.utc)
    system_prompts_db[prompt_id] = {
        "id": prompt_id,
        "content": data.content,
        "description": data.description,
        "owner_email": current_user["email"],
        "created_at": now,
        "updated_at": now,
    }
    return system_prompts_db[prompt_id]


@router.patch("/system-prompts/{id}", response_model=SystemPromptResponse)
def update_system_prompt(
    id: str,
    data: SystemPromptUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    prompt = _get_or_404(system_prompts_db, id, "System prompt")
    _require_owner(prompt, current_user["email"], "system prompt")
    if data.content is not None:
        prompt["content"] = data.content
    if data.description is not None:
        prompt["description"] = data.description
    prompt["updated_at"] = datetime.now(timezone.utc)
    return prompt


@router.delete("/system-prompts/{id}", status_code=204)
def delete_system_prompt(id: str, current_user: dict = Depends(get_current_user)):
    prompt = _get_or_404(system_prompts_db, id, "System prompt")
    _require_owner(prompt, current_user["email"], "system prompt")
    del system_prompts_db[id]
    return None


# ─── Developer Prompts ───

@router.get("/developer-prompts", response_model=list[DeveloperPromptResponse])
def list_developer_prompts(current_user: dict = Depends(get_current_user)):
    return [p for p in developer_prompts_db.values() if p["owner_email"] == current_user["email"]]


@router.post("/developer-prompts", response_model=DeveloperPromptResponse, status_code=201)
def create_developer_prompt(
    data: DeveloperPromptCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    prompt_id = str(uuid4())
    now = datetime.now(timezone.utc)
    developer_prompts_db[prompt_id] = {
        "id": prompt_id,
        "content": data.content,
        "description": data.description,
        "owner_email": current_user["email"],
        "created_at": now,
        "updated_at": now,
    }
    return developer_prompts_db[prompt_id]


@router.patch("/developer-prompts/{id}", response_model=DeveloperPromptResponse)
def update_developer_prompt(
    id: str,
    data: DeveloperPromptUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    prompt = _get_or_404(developer_prompts_db, id, "Developer prompt")
    _require_owner(prompt, current_user["email"], "developer prompt")
    if data.content is not None:
        prompt["content"] = data.content
    if data.description is not None:
        prompt["description"] = data.description
    prompt["updated_at"] = datetime.now(timezone.utc)
    return prompt


@router.delete("/developer-prompts/{id}", status_code=204)
def delete_developer_prompt(id: str, current_user: dict = Depends(get_current_user)):
    prompt = _get_or_404(developer_prompts_db, id, "Developer prompt")
    _require_owner(prompt, current_user["email"], "developer prompt")
    del developer_prompts_db[id]
    return None