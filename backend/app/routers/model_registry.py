"""
Model Registry router — CRUD, register, archive, restore.
Matches the Model Registry section of the Model Management APIs
blueprint (8/8). Only the model owner can update/delete/archive/restore
their own model. Mirrors the structure of projects.py / prompts.py.

ASSUMPTIONS:
- POST /models creates a NEW model record from scratch (source="created").
- POST /models/register is for referencing an ALREADY-EXISTING model
  artifact from elsewhere (e.g. an external provider/registry) — it takes
  an external_id instead of a base_model, and the resulting record has
  source="registered". Both endpoints ultimately create a row in the same
  models_db, just with different provenance metadata.
- This registry only stores model METADATA — no actual model weights,
  files, or provider API credentials are stored or transmitted anywhere.

Literal-path routes (/register, /archive, /restore) MUST come before the
dynamic /{id} routes below — same ordering rule used throughout this
codebase.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.model_registry import (
    ModelCreateRequest,
    ModelRegisterRequest,
    ModelUpdateRequest,
    ModelOut,
    ModelIdBodyRequest,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/models", tags=["Model Registry"])

# id -> {id, name, provider, base_model, external_id, source, status, owner_email, created_at, updated_at}
models_db: dict[str, dict] = {}


def _get_model_or_404(id: str) -> dict:
    model = models_db.get(id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model


def _require_owner(model: dict, email: str):
    if model["owner_email"] != email:
        raise HTTPException(status_code=403, detail="Only the model owner can perform this action")


@router.get("", response_model=list[ModelOut])
def list_models(current_user: dict = Depends(get_current_user)):
    return [m for m in models_db.values() if m["owner_email"] == current_user["email"]]


@router.post("", response_model=ModelOut, status_code=201)
def create_model(data: ModelCreateRequest, current_user: dict = Depends(get_current_user)):
    model_id = str(uuid4())
    now = datetime.now(timezone.utc)
    models_db[model_id] = {
        "id": model_id,
        "name": data.name,
        "provider": data.provider,
        "base_model": data.base_model,
        "external_id": None,
        "source": "created",
        "status": "active",
        "owner_email": current_user["email"],
        "created_at": now,
        "updated_at": now,
    }
    return models_db[model_id]


# ─── Literal-path routes MUST come before any /{id} routes below ───

@router.post("/register", response_model=ModelOut, status_code=201)
def register_model(data: ModelRegisterRequest, current_user: dict = Depends(get_current_user)):
    model_id = str(uuid4())
    now = datetime.now(timezone.utc)
    models_db[model_id] = {
        "id": model_id,
        "name": data.name,
        "provider": data.provider,
        "base_model": None,
        "external_id": data.external_id,
        "source": "registered",
        "status": "active",
        "owner_email": current_user["email"],
        "created_at": now,
        "updated_at": now,
    }
    return models_db[model_id]


@router.post("/archive", response_model=ModelOut)
def archive_model(data: ModelIdBodyRequest, current_user: dict = Depends(get_current_user)):
    model = _get_model_or_404(data.model_id)
    _require_owner(model, current_user["email"])
    model["status"] = "archived"
    model["updated_at"] = datetime.now(timezone.utc)
    return model


@router.post("/restore", response_model=ModelOut)
def restore_model(data: ModelIdBodyRequest, current_user: dict = Depends(get_current_user)):
    model = _get_model_or_404(data.model_id)
    _require_owner(model, current_user["email"])
    model["status"] = "active"
    model["updated_at"] = datetime.now(timezone.utc)
    return model


# ─── Dynamic /{id} routes come LAST ───

@router.get("/{id}", response_model=ModelOut)
def get_model(id: str, current_user: dict = Depends(get_current_user)):
    model = _get_model_or_404(id)
    _require_owner(model, current_user["email"])
    return model


@router.patch("/{id}", response_model=ModelOut)
def update_model(id: str, data: ModelUpdateRequest, current_user: dict = Depends(get_current_user)):
    model = _get_model_or_404(id)
    _require_owner(model, current_user["email"])
    if data.name is not None:
        model["name"] = data.name
    if data.provider is not None:
        model["provider"] = data.provider
    if data.base_model is not None:
        model["base_model"] = data.base_model
    model["updated_at"] = datetime.now(timezone.utc)
    return model


@router.delete("/{id}", status_code=204)
def delete_model(id: str, current_user: dict = Depends(get_current_user)):
    model = _get_model_or_404(id)
    _require_owner(model, current_user["email"])
    del models_db[id]
    return None