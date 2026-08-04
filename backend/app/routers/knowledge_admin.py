"""
Knowledge Administration router — config, reindex, validate, migrate,
backup, restore-backup, version.
Matches the Administration section of the Knowledge / RAG APIs blueprint
(8/8).

ASSUMPTIONS:
- Config is a single GLOBAL, platform-wide setting (chunk_size,
  chunk_overlap, embedding_model, auto_reindex) — not per-user. This
  matches the "Administration" framing of this section (system-level
  settings), same pattern as networking.py.
- SAME CAVEAT AS networking.py / scaling.py: there is NO admin-role
  restriction here — any authenticated user can currently PATCH the
  config, trigger a migration, or restore a backup. This is almost
  certainly too permissive for a real deployment; add a role check
  (roles.py/permissions.py exist in this codebase) before relying on
  this for anything real.
- POST /knowledge/reindex, /knowledge/migrate, /knowledge/backup, and
  /knowledge/restore-backup are all STUBS: they record that an action
  was "triggered" and report success immediately. There is no real
  reindexing pipeline, no real schema migration, and no real backup
  storage behind any of them.
- POST /knowledge/validate runs simple, real sanity checks against the
  CURRENT in-memory config (e.g. chunk_overlap must be smaller than
  chunk_size) — this part is genuinely computed from real config state,
  just very basic.

No route-ordering concerns: /knowledge/config, /knowledge/reindex,
/knowledge/validate, /knowledge/migrate, /knowledge/backup,
/knowledge/restore-backup, /knowledge/version are all flat, distinct
literal paths, with GET/PATCH on the same "/knowledge/config" path
distinguished by method (no ordering issue, same as vector_index.py's
GET/POST/DELETE on "/index").
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.knowledge_admin import (
    KnowledgeConfigUpdateRequest,
    KnowledgeConfigResponse,
    ReindexResponse,
    ValidateResponse,
    MigrateRequest,
    MigrateResponse,
    BackupResponse,
    RestoreBackupRequest,
    RestoreBackupResponse,
    VersionResponse,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/knowledge", tags=["Knowledge Administration"])

_API_VERSION = "v1"

# Global, platform-wide state (see docstring).
_config: dict = {
    "chunk_size": 512,
    "chunk_overlap": 50,
    "embedding_model": "text-embedding-3-small",
    "auto_reindex": False,
    "updated_at": datetime.now(timezone.utc),
}

_config_version = "1"
_last_migrated_at: datetime | None = None

# id -> {id, status, created_at}
_backups_db: dict[str, dict] = {}


@router.get("/config", response_model=KnowledgeConfigResponse)
def get_knowledge_config():
    return _config


@router.patch("/config", response_model=KnowledgeConfigResponse)
def update_knowledge_config(
    data: KnowledgeConfigUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    global _config_version
    if data.chunk_size is not None:
        _config["chunk_size"] = data.chunk_size
    if data.chunk_overlap is not None:
        _config["chunk_overlap"] = data.chunk_overlap
    if data.embedding_model is not None:
        _config["embedding_model"] = data.embedding_model
    if data.auto_reindex is not None:
        _config["auto_reindex"] = data.auto_reindex
    _config["updated_at"] = datetime.now(timezone.utc)
    _config_version = str(int(_config_version) + 1)
    return _config


@router.post("/reindex", response_model=ReindexResponse, status_code=201)
def trigger_reindex(current_user: dict = Depends(get_current_user)):
    return ReindexResponse(
        id=str(uuid4()), status="completed",
        triggered_by=current_user["email"], started_at=datetime.now(timezone.utc),
    )


@router.post("/validate", response_model=ValidateResponse)
def validate_knowledge_config():
    issues: list[str] = []
    if _config["chunk_overlap"] >= _config["chunk_size"]:
        issues.append("chunk_overlap must be smaller than chunk_size")
    if _config["chunk_size"] <= 0:
        issues.append("chunk_size must be positive")
    if not _config["embedding_model"]:
        issues.append("embedding_model is not set")
    return ValidateResponse(valid=len(issues) == 0, issues=issues, checked_at=datetime.now(timezone.utc))


@router.post("/migrate", response_model=MigrateResponse, status_code=201)
def migrate_knowledge_base(data: MigrateRequest, current_user: dict = Depends(get_current_user)):
    global _config_version, _last_migrated_at
    from_version = _config_version
    now = datetime.now(timezone.utc)
    _config_version = data.target_version
    _last_migrated_at = now
    return MigrateResponse(
        id=str(uuid4()), from_version=from_version, to_version=data.target_version,
        status="completed", migrated_at=now,
    )


@router.post("/backup", response_model=BackupResponse, status_code=201)
def create_knowledge_backup(current_user: dict = Depends(get_current_user)):
    backup_id = str(uuid4())
    now = datetime.now(timezone.utc)
    _backups_db[backup_id] = {"id": backup_id, "status": "completed", "created_at": now}
    return _backups_db[backup_id]


@router.post("/restore-backup", response_model=RestoreBackupResponse)
def restore_knowledge_backup(data: RestoreBackupRequest, current_user: dict = Depends(get_current_user)):
    backup = _backups_db.get(data.backup_id)
    if not backup:
        raise HTTPException(status_code=404, detail="Backup not found")
    now = datetime.now(timezone.utc)
    return RestoreBackupResponse(
        id=str(uuid4()), backup_id=data.backup_id, status="restored", restored_at=now,
    )


@router.get("/version", response_model=VersionResponse)
def get_knowledge_version():
    return VersionResponse(
        api_version=_API_VERSION, config_version=_config_version, last_migrated_at=_last_migrated_at,
    )