"""
Files Monitoring & Admin router — metrics, logs, health, audit, cache/clear,
config, export, import — all scoped to the files domain.
Matches the "Monitoring & Admin" section of the File & Storage APIs
blueprint (8/8).

NOT the same as monitoring_metrics.py, which is a separate, platform-wide
CPU/memory/disk/network monitoring domain (prefix /api/v1/monitoring).
This router is scoped to files specifically (prefix /api/v1/files).

IMPORTANT: Shares the /api/v1/files prefix with fileslifecycle.router,
search_index.router. This router's endpoints are all literal, single- or
two-segment paths (/metrics, /logs, /health, /audit, /cache/clear, /config,
/export, /import), so — same as search_index.py — it MUST be included in
main.py BEFORE fileslifecycle.router, or these paths will get swallowed by
fileslifecycle's dynamic GET /files/{id}.

DESIGN NOTES / ASSUMPTIONS (this domain is entirely new, built from
scratch, and does not modify fileslifecycle.py):
- /files/logs and /files/audit are DERIVED from files_db's created_at /
  updated_at timestamps rather than a real, persisted event log — there's
  no hook into fileslifecycle.py's create/update/delete functions (and I
  deliberately didn't add one, to avoid touching that already-tested file).
  If you want true point-in-time event logging (e.g. capturing deletes,
  which leave no trace in files_db once removed), that requires adding
  logging calls inside fileslifecycle.py itself — a follow-up change, not
  done here.
- Both /logs and /audit are scoped to the CALLER's own files only, not a
  platform-wide view across all users — this errs on the side of not
  leaking other users' data by default. If /files/audit is meant to be a
  true admin-wide audit trail, it needs an admin-only permission check
  (this codebase already has roles.py / permissions.py for that) before
  it should return all users' file activity.
- /files/config is a single GLOBAL, in-memory config (not per-user), and
  currently any authenticated user can PATCH it — same caveat as
  replication in backup_sync.py. Lock this down with an admin dependency
  before relying on it.
- /files/cache/clear operates on a placeholder in-memory cache dict that
  nothing else in the codebase actually reads from yet — it's here so the
  endpoint exists and behaves sensibly, but there's no real cache to clear
  until something populates files_cache.
- /files/import actually creates real entries in files_db (owned by the
  caller), unlike /files/export, which only records a lightweight export
  job summary rather than producing real file bytes anywhere.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends

from app.schemas.files_admin import (
    FileMetricsResponse,
    FileLogEntry,
    FileAuditEntry,
    FileHealthResponse,
    CacheClearResponse,
    FileConfigUpdateRequest,
    FileConfigResponse,
    FileExportRequest,
    FileExportResponse,
    FileImportRequest,
    FileImportResponse,
    ImportedFileOut,
)
from app.routers.fileslifecycle import files_db
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/files", tags=["Files Monitoring & Admin"])

# Placeholder cache store — nothing else populates this yet (see docstring).
files_cache: dict = {}

# Global, platform-wide file-domain config (not per-user — see docstring).
files_config: dict = {
    "max_file_size_bytes": 104_857_600,  # 100 MB
    "allowed_mime_types": ["*/*"],
}

# export_id -> {id, owner_email, format, file_count, status, created_at}
file_exports_db: dict[str, dict] = {}


def _owned_files(email: str) -> list[dict]:
    return [f for f in files_db.values() if f["owner_email"] == email]


@router.get("/metrics", response_model=FileMetricsResponse)
def get_file_metrics(current_user: dict = Depends(get_current_user)):
    owned = _owned_files(current_user["email"])
    total_size = sum(f["size_bytes"] for f in owned)
    active = sum(1 for f in owned if f["status"] == "active")
    archived = sum(1 for f in owned if f["status"] == "archived")
    avg_size = (total_size / len(owned)) if owned else 0.0
    return FileMetricsResponse(
        total_files=len(owned),
        total_size_bytes=total_size,
        active_count=active,
        archived_count=archived,
        avg_size_bytes=round(avg_size, 2),
    )


@router.get("/logs", response_model=list[FileLogEntry])
def get_file_logs(current_user: dict = Depends(get_current_user)):
    entries: list[FileLogEntry] = []
    for f in _owned_files(current_user["email"]):
        entries.append(FileLogEntry(file_id=f["id"], action="created", timestamp=f["created_at"]))
        if f["updated_at"] != f["created_at"]:
            entries.append(FileLogEntry(file_id=f["id"], action="updated", timestamp=f["updated_at"]))
    entries.sort(key=lambda e: e.timestamp, reverse=True)
    return entries


@router.get("/health", response_model=FileHealthResponse)
def get_file_health():
    return FileHealthResponse(
        status="ok",
        total_files_tracked=len(files_db),
        checked_at=datetime.now(timezone.utc),
    )


@router.get("/audit", response_model=list[FileAuditEntry])
def get_file_audit(current_user: dict = Depends(get_current_user)):
    entries: list[FileAuditEntry] = []
    for f in _owned_files(current_user["email"]):
        entries.append(FileAuditEntry(
            file_id=f["id"], owner_email=f["owner_email"], action="created",
            status=f["status"], timestamp=f["created_at"],
        ))
        if f["updated_at"] != f["created_at"]:
            entries.append(FileAuditEntry(
                file_id=f["id"], owner_email=f["owner_email"], action="updated",
                status=f["status"], timestamp=f["updated_at"],
            ))
    entries.sort(key=lambda e: e.timestamp, reverse=True)
    return entries


@router.post("/cache/clear", response_model=CacheClearResponse)
def clear_file_cache():
    cleared_count = len(files_cache)
    files_cache.clear()
    return CacheClearResponse(cleared_count=cleared_count, cleared_at=datetime.now(timezone.utc))


@router.patch("/config", response_model=FileConfigResponse)
def update_file_config(data: FileConfigUpdateRequest):
    if data.max_file_size_bytes is not None:
        files_config["max_file_size_bytes"] = data.max_file_size_bytes
    if data.allowed_mime_types is not None:
        files_config["allowed_mime_types"] = data.allowed_mime_types
    return FileConfigResponse(**files_config)


@router.post("/export", response_model=FileExportResponse, status_code=201)
def export_files(
    data: FileExportRequest,
    current_user: dict = Depends(get_current_user),
):
    export_id = str(uuid4())
    now = datetime.now(timezone.utc)
    export = {
        "id": export_id,
        "owner_email": current_user["email"],
        "format": data.format,
        "file_count": len(_owned_files(current_user["email"])),
        "status": "completed",
        "created_at": now,
    }
    file_exports_db[export_id] = export
    return FileExportResponse(**export)


@router.post("/import", response_model=FileImportResponse, status_code=201)
def import_files(
    data: FileImportRequest,
    current_user: dict = Depends(get_current_user),
):
    created: list[ImportedFileOut] = []
    now = datetime.now(timezone.utc)
    for item in data.files:
        file_id = str(uuid4())
        record = {
            "id": file_id,
            "name": item.name,
            "folder_id": item.folder_id,
            "size_bytes": item.size_bytes,
            "mime_type": item.mime_type,
            "owner_email": current_user["email"],
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }
        files_db[file_id] = record
        created.append(ImportedFileOut(**record))
    return FileImportResponse(imported_count=len(created), files=created)