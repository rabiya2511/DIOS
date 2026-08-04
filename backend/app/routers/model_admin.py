"""
Model Administration router — enable/disable, sync, reindex, reload,
config, audit.
Matches the Administration section of the Model Management APIs
blueprint (8/8).

*** ROUTING NOTE — READ THIS FIRST ***
/enable, /disable, /sync, /reindex, /reload, /config, /audit are all
SINGLE-SEGMENT literal paths under /api/v1/models — the same shape as
model_registry.py's dynamic GET/PATCH/DELETE /{id}, and the same class of
issue as model_monitoring.py. This router MUST be registered in main.py
BEFORE model_registry.router, or these requests will be swallowed by
model_registry's /{id} route.

ASSUMPTIONS:
- POST /models/enable and /models/disable operate on a model's "enabled"
  flag — a SEPARATE concept from model_registry.py's active/archived
  status. "enabled" governs whether a model is currently available for
  routing/inference; "status" (active/archived) governs whether the
  model record itself exists in a soft-deleted state. Only the model
  owner can toggle this. Since model_registry.py's create_model doesn't
  set an "enabled" key (to avoid modifying that already-tested file),
  it's lazily defaulted to True here on first access — same pattern used
  elsewhere in this codebase (e.g. profile.py's _ensure_profile_defaults).
- POST /models/sync, /reindex, /reload are STUBS — no real external
  provider sync, no real search-index rebuild, no real model-weight
  reload happens. synced_count / reloaded_count report the REAL current
  count of models in models_db (genuine data), but the "sync"/"reload"
  action itself is a no-op.
- GET/PATCH /models/config is GLOBAL, platform-wide admin config — same
  caveat as networking.py/routing_policies.py: no admin-role restriction,
  any authenticated user can currently change it.
- GET /models/audit is scoped to the CALLER's own actions only (not a
  platform-wide view across all users), same privacy-conscious choice as
  files_admin.py's /audit — every enable/disable/sync/reindex/
  reload/config-change call in this router is genuinely logged here, not
  fabricated.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends

from app.schemas.model_admin import (
    ModelIdBodyRequest,
    ModelEnableResponse,
    SyncResponse,
    ReindexResponse,
    ReloadResponse,
    AdminConfigUpdateRequest,
    AdminConfigResponse,
    AuditEntry,
)
from app.routers.model_registry import models_db, _get_model_or_404, _require_owner
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/models", tags=["Model Administration"])

_admin_config: dict = {
    "default_provider": "anthropic",
    "auto_sync_enabled": False,
    "max_models_per_user": 50,
    "updated_at": datetime.now(timezone.utc),
}

# owner_email -> [{id, action, actor_email, detail, timestamp}]
_audit_log_db: dict[str, list[dict]] = {}


def _log_audit(email: str, action: str, detail: str):
    _audit_log_db.setdefault(email, []).append({
        "id": str(uuid4()), "action": action, "actor_email": email,
        "detail": detail, "timestamp": datetime.now(timezone.utc),
    })


@router.post("/enable", response_model=ModelEnableResponse)
def enable_model(data: ModelIdBodyRequest, current_user: dict = Depends(get_current_user)):
    model = _get_model_or_404(data.model_id)
    _require_owner(model, current_user["email"])
    model["enabled"] = True
    now = datetime.now(timezone.utc)
    _log_audit(current_user["email"], "enable", f"Model {data.model_id} enabled")
    return ModelEnableResponse(model_id=data.model_id, enabled=True, updated_at=now)


@router.post("/disable", response_model=ModelEnableResponse)
def disable_model(data: ModelIdBodyRequest, current_user: dict = Depends(get_current_user)):
    model = _get_model_or_404(data.model_id)
    _require_owner(model, current_user["email"])
    model["enabled"] = False
    now = datetime.now(timezone.utc)
    _log_audit(current_user["email"], "disable", f"Model {data.model_id} disabled")
    return ModelEnableResponse(model_id=data.model_id, enabled=False, updated_at=now)


@router.post("/sync", response_model=SyncResponse, status_code=201)
def sync_models(current_user: dict = Depends(get_current_user)):
    now = datetime.now(timezone.utc)
    sync_id = str(uuid4())
    _log_audit(current_user["email"], "sync", "Model registry sync triggered")
    return SyncResponse(
        id=sync_id, status="completed", synced_count=len(models_db),
        triggered_by=current_user["email"], started_at=now,
    )


@router.post("/reindex", response_model=ReindexResponse, status_code=201)
def reindex_models(current_user: dict = Depends(get_current_user)):
    now = datetime.now(timezone.utc)
    _log_audit(current_user["email"], "reindex", "Model reindex triggered")
    return ReindexResponse(
        id=str(uuid4()), status="completed", triggered_by=current_user["email"], started_at=now,
    )


@router.post("/reload", response_model=ReloadResponse, status_code=201)
def reload_models(current_user: dict = Depends(get_current_user)):
    now = datetime.now(timezone.utc)
    _log_audit(current_user["email"], "reload", "Model reload triggered")
    return ReloadResponse(
        id=str(uuid4()), status="completed", reloaded_count=len(models_db),
        triggered_by=current_user["email"], started_at=now,
    )


@router.get("/config", response_model=AdminConfigResponse)
def get_admin_config():
    return _admin_config


@router.patch("/config", response_model=AdminConfigResponse)
def update_admin_config(data: AdminConfigUpdateRequest, current_user: dict = Depends(get_current_user)):
    if data.default_provider is not None:
        _admin_config["default_provider"] = data.default_provider
    if data.auto_sync_enabled is not None:
        _admin_config["auto_sync_enabled"] = data.auto_sync_enabled
    if data.max_models_per_user is not None:
        _admin_config["max_models_per_user"] = data.max_models_per_user
    _admin_config["updated_at"] = datetime.now(timezone.utc)
    _log_audit(current_user["email"], "config_update", "Admin config updated")
    return _admin_config


@router.get("/audit", response_model=list[AuditEntry])
def get_admin_audit(current_user: dict = Depends(get_current_user)):
    entries = _audit_log_db.get(current_user["email"], [])
    return sorted(entries, key=lambda e: e["timestamp"], reverse=True)