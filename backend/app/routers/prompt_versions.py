"""
Versioning router — list/create/update/delete versions, promote,
rollback, history, compare. Matches the Versioning section of the
Prompt Management APIs blueprint (8/8). All paths are 3+ segments
under /prompts/{id}/..., distinct from prompts.py's 1-2 segment
routes, so registration order relative to it doesn't matter.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.prompt_versions import (
    VersionResponse,
    VersionCreateRequest,
    VersionUpdateRequest,
    VersionActionRequest,
    HistoryEntry,
    CompareRequest,
    CompareResponse,
)
from app.routers.prompts import prompts_db, _get_prompt_or_404, _require_owner
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/prompts", tags=["Versioning"])

# prompt_id -> list of {version, title, content, tags, created_at}
prompt_versions_db: dict[str, list] = {}

# append-only audit log
version_history_db: list[dict] = []


def _log_history(prompt_id: str, action: str, version: int | None = None):
    version_history_db.append(
        {
            "prompt_id": prompt_id,
            "action": action,
            "version": version,
            "timestamp": datetime.now(timezone.utc),
        }
    )


def _get_version_or_404(prompt_id: str, version: int) -> dict:
    versions = prompt_versions_db.get(prompt_id, [])
    match = next((v for v in versions if v["version"] == version), None)
    if not match:
        raise HTTPException(status_code=404, detail=f"Version {version} not found for this prompt")
    return match


@router.get("/{id}/versions", response_model=list[VersionResponse])
def list_versions(id: str, current_user: dict = Depends(get_current_user)):
    prompt = _get_prompt_or_404(id)
    _require_owner(prompt, current_user["email"])
    return prompt_versions_db.get(id, [])


@router.post("/{id}/versions", response_model=VersionResponse, status_code=201)
def create_version(
    id: str,
    data: VersionCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    prompt = _get_prompt_or_404(id)
    _require_owner(prompt, current_user["email"])

    versions = prompt_versions_db.setdefault(id, [])
    next_version = (versions[-1]["version"] + 1) if versions else 1
    now = datetime.now(timezone.utc)
    snapshot = {
        "version": next_version,
        "title": data.title if data.title is not None else prompt["title"],
        "content": data.content if data.content is not None else prompt["content"],
        "tags": data.tags if data.tags is not None else list(prompt["tags"]),
        "created_at": now,
    }
    versions.append(snapshot)
    _log_history(id, "version_created", next_version)
    return snapshot


@router.patch("/{id}/versions/{version}", response_model=VersionResponse)
def update_version(
    id: str,
    version: int,
    data: VersionUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    prompt = _get_prompt_or_404(id)
    _require_owner(prompt, current_user["email"])
    snapshot = _get_version_or_404(id, version)

    if data.title is not None:
        snapshot["title"] = data.title
    if data.content is not None:
        snapshot["content"] = data.content
    if data.tags is not None:
        snapshot["tags"] = data.tags
    _log_history(id, "version_updated", version)
    return snapshot


@router.delete("/{id}/versions/{version}", status_code=204)
def delete_version(
    id: str,
    version: int,
    current_user: dict = Depends(get_current_user),
):
    prompt = _get_prompt_or_404(id)
    _require_owner(prompt, current_user["email"])
    _get_version_or_404(id, version)

    prompt_versions_db[id] = [v for v in prompt_versions_db[id] if v["version"] != version]
    _log_history(id, "version_deleted", version)
    return None


def _apply_version(prompt: dict, snapshot: dict):
    prompt["title"] = snapshot["title"]
    prompt["content"] = snapshot["content"]
    prompt["tags"] = list(snapshot["tags"])
    prompt["updated_at"] = datetime.now(timezone.utc)


@router.post("/{id}/promote", response_model=VersionResponse)
def promote_version(
    id: str,
    data: VersionActionRequest,
    current_user: dict = Depends(get_current_user),
):
    prompt = _get_prompt_or_404(id)
    _require_owner(prompt, current_user["email"])
    snapshot = _get_version_or_404(id, data.version)

    _apply_version(prompt, snapshot)
    _log_history(id, "promoted", data.version)
    return snapshot


@router.post("/{id}/rollback", response_model=VersionResponse)
def rollback_version(
    id: str,
    data: VersionActionRequest,
    current_user: dict = Depends(get_current_user),
):
    prompt = _get_prompt_or_404(id)
    _require_owner(prompt, current_user["email"])
    snapshot = _get_version_or_404(id, data.version)

    _apply_version(prompt, snapshot)
    _log_history(id, "rolled_back", data.version)
    return snapshot


@router.get("/{id}/history", response_model=list[HistoryEntry])
def get_history(id: str, current_user: dict = Depends(get_current_user)):
    prompt = _get_prompt_or_404(id)
    _require_owner(prompt, current_user["email"])
    return [h for h in version_history_db if h["prompt_id"] == id]


@router.post("/{id}/compare", response_model=CompareResponse)
def compare_versions(
    id: str,
    data: CompareRequest,
    current_user: dict = Depends(get_current_user),
):
    prompt = _get_prompt_or_404(id)
    _require_owner(prompt, current_user["email"])
    v_a = _get_version_or_404(id, data.version_a)
    v_b = _get_version_or_404(id, data.version_b)

    return CompareResponse(
        version_a=data.version_a,
        version_b=data.version_b,
        title_changed=v_a["title"] != v_b["title"],
        content_changed=v_a["content"] != v_b["content"],
        tags_changed=set(v_a["tags"]) != set(v_b["tags"]),
    )