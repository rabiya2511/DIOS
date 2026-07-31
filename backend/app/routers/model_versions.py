"""
Model Versions router — list/create/update/delete versions, promote,
rollback, changelog, clone. Matches the Model Versions section of the
Model Management APIs blueprint (8/8). Builds on models_db from
model_registry.py. All paths are 3+ segments under /models/{id}/...,
distinct from model_registry.py's 1-2 segment routes — no ordering
dependency relative to it.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.model_versions import (
    ModelVersionResponse,
    ModelVersionCreateRequest,
    ModelVersionUpdateRequest,
    ModelVersionActionRequest,
    ModelChangelogEntry,
    ModelCloneRequest,
)
from app.schemas.model_registry import ModelOut
from app.routers.model_registry import models_db, _get_model_or_404, _require_owner
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/models", tags=["Model Versions"])

# model_id -> list of {version, name, provider, base_model, created_at}
model_versions_db: dict[str, list] = {}

# append-only audit log
model_version_history_db: list[dict] = []


def _log_history(model_id: str, action: str, version: int | None = None):
    model_version_history_db.append(
        {
            "model_id": model_id,
            "action": action,
            "version": version,
            "timestamp": datetime.now(timezone.utc),
        }
    )


def _get_version_or_404(model_id: str, version: int) -> dict:
    versions = model_versions_db.get(model_id, [])
    match = next((v for v in versions if v["version"] == version), None)
    if not match:
        raise HTTPException(status_code=404, detail=f"Version {version} not found for this model")
    return match


@router.get("/{id}/versions", response_model=list[ModelVersionResponse])
def list_versions(id: str, current_user: dict = Depends(get_current_user)):
    model = _get_model_or_404(id)
    _require_owner(model, current_user["email"])
    return model_versions_db.get(id, [])


@router.post("/{id}/versions", response_model=ModelVersionResponse, status_code=201)
def create_version(
    id: str,
    data: ModelVersionCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    model = _get_model_or_404(id)
    _require_owner(model, current_user["email"])

    versions = model_versions_db.setdefault(id, [])
    next_version = (versions[-1]["version"] + 1) if versions else 1
    now = datetime.now(timezone.utc)
    snapshot = {
        "version": next_version,
        "name": data.name if data.name is not None else model["name"],
        "provider": data.provider if data.provider is not None else model["provider"],
        "base_model": data.base_model if data.base_model is not None else model["base_model"],
        "created_at": now,
    }
    versions.append(snapshot)
    _log_history(id, "version_created", next_version)
    return snapshot


@router.patch("/{id}/versions/{version}", response_model=ModelVersionResponse)
def update_version(
    id: str,
    version: int,
    data: ModelVersionUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    model = _get_model_or_404(id)
    _require_owner(model, current_user["email"])
    snapshot = _get_version_or_404(id, version)

    if data.name is not None:
        snapshot["name"] = data.name
    if data.provider is not None:
        snapshot["provider"] = data.provider
    if data.base_model is not None:
        snapshot["base_model"] = data.base_model
    _log_history(id, "version_updated", version)
    return snapshot


@router.delete("/{id}/versions/{version}", status_code=204)
def delete_version(id: str, version: int, current_user: dict = Depends(get_current_user)):
    model = _get_model_or_404(id)
    _require_owner(model, current_user["email"])
    _get_version_or_404(id, version)

    model_versions_db[id] = [v for v in model_versions_db[id] if v["version"] != version]
    _log_history(id, "version_deleted", version)
    return None


def _apply_version(model: dict, snapshot: dict):
    model["name"] = snapshot["name"]
    model["provider"] = snapshot["provider"]
    model["base_model"] = snapshot["base_model"]
    model["updated_at"] = datetime.now(timezone.utc)


@router.post("/{id}/promote", response_model=ModelVersionResponse)
def promote_version(
    id: str,
    data: ModelVersionActionRequest,
    current_user: dict = Depends(get_current_user),
):
    model = _get_model_or_404(id)
    _require_owner(model, current_user["email"])
    snapshot = _get_version_or_404(id, data.version)

    _apply_version(model, snapshot)
    _log_history(id, "promoted", data.version)
    return snapshot


@router.post("/{id}/rollback", response_model=ModelVersionResponse)
def rollback_version(
    id: str,
    data: ModelVersionActionRequest,
    current_user: dict = Depends(get_current_user),
):
    model = _get_model_or_404(id)
    _require_owner(model, current_user["email"])
    snapshot = _get_version_or_404(id, data.version)

    _apply_version(model, snapshot)
    _log_history(id, "rolled_back", data.version)
    return snapshot


@router.get("/{id}/changelog", response_model=list[ModelChangelogEntry])
def get_changelog(id: str, current_user: dict = Depends(get_current_user)):
    model = _get_model_or_404(id)
    _require_owner(model, current_user["email"])
    return [h for h in model_version_history_db if h["model_id"] == id]


@router.post("/{id}/clone", response_model=ModelOut, status_code=201)
def clone_model(
    id: str,
    data: ModelCloneRequest,
    current_user: dict = Depends(get_current_user),
):
    original = _get_model_or_404(id)
    _require_owner(original, current_user["email"])

    new_id = str(uuid4())
    now = datetime.now(timezone.utc)
    models_db[new_id] = {
        "id": new_id,
        "name": data.new_name or f"{original['name']} (copy)",
        "provider": original["provider"],
        "base_model": original["base_model"],
        "external_id": original["external_id"],
        "source": original["source"],
        "status": "active",
        "owner_email": current_user["email"],
        "created_at": now,
        "updated_at": now,
    }
    _log_history(id, "cloned")
    return models_db[new_id]