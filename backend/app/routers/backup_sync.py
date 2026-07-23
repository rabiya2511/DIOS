"""
Backup & Sync router — backup create/restore/history, sync start/stop/status,
replication start/status.
Matches the Backup & Sync section of the File & Storage APIs blueprint (8/8).

ASSUMPTIONS:
- Backup is per-user: POST /backup/create snapshots the count of the caller's
  currently owned files (from fileslifecycle.files_db) as a lightweight
  in-memory record. It does NOT actually copy file bytes anywhere — this is a
  stub, same spirit as the "STUBBED" comments in fileslifecycle.py /
  organizations.py.
- POST /backup/restore is also stubbed: it marks the backup as "restored" and
  returns it, but does not actually recreate files in files_db. Wire that up
  once real storage/versioning exists.
- Sync (POST /sync/start, /sync/stop, GET /sync/status) is per-user state —
  each user has their own independent sync session.
- Replication (POST /replication/start, GET /replication/status) is treated
  as a single GLOBAL, platform-wide state rather than per-user, since
  replication is normally an infrastructure-level concern, not a per-account
  one. Any authenticated user can currently trigger it — add an admin-only
  dependency if that's too permissive for your use case.
- This router uses its own top-level prefix ("/api/v1") rather than
  "/api/v1/files", since /backup and /sync/replication are not nested under
  /files in the blueprint. No route-ordering conflicts with other routers as
  a result.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.backup_sync import (
    BackupCreateRequest,
    BackupOut,
    BackupRestoreRequest,
    SyncStatusResponse,
    ReplicationStatusResponse,
)
from app.routers.fileslifecycle import files_db
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1", tags=["Backup & Sync"])

# backup_id -> {id, owner_email, label, file_count, status, created_at}
backups_db: dict[str, dict] = {}

# owner_email -> {status, started_at, stopped_at}
sync_state: dict[str, dict] = {}

# Global, platform-wide replication state (not per-user — see docstring).
replication_state: dict = {
    "status": "idle",
    "started_at": None,
    "stopped_at": None,
}


def _owned_file_count(email: str) -> int:
    return sum(1 for f in files_db.values() if f["owner_email"] == email)


def _get_backup_or_404(backup_id: str) -> dict:
    backup = backups_db.get(backup_id)
    if not backup:
        raise HTTPException(status_code=404, detail="Backup not found")
    return backup


def _require_backup_owner(backup: dict, email: str):
    if backup["owner_email"] != email:
        raise HTTPException(status_code=403, detail="Only the backup owner can perform this action")


def _get_sync_state(email: str) -> dict:
    if email not in sync_state:
        sync_state[email] = {"status": "idle", "started_at": None, "stopped_at": None}
    return sync_state[email]


@router.post("/backup/create", response_model=BackupOut, status_code=201)
def create_backup(
    data: BackupCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    backup_id = str(uuid4())
    now = datetime.now(timezone.utc)
    backup = {
        "id": backup_id,
        "owner_email": current_user["email"],
        "label": data.label,
        "file_count": _owned_file_count(current_user["email"]),
        "status": "completed",
        "created_at": now,
    }
    backups_db[backup_id] = backup
    return BackupOut(**backup)


@router.post("/backup/restore", response_model=BackupOut)
def restore_backup(
    data: BackupRestoreRequest,
    current_user: dict = Depends(get_current_user),
):
    backup = _get_backup_or_404(data.backup_id)
    _require_backup_owner(backup, current_user["email"])
    # STUB: real version would recreate/overwrite files in files_db from the
    # snapshot. Here we just flag the backup as restored.
    backup["status"] = "restored"
    return BackupOut(**backup)


@router.get("/backup/history", response_model=list[BackupOut])
def backup_history(current_user: dict = Depends(get_current_user)):
    return [
        BackupOut(**b) for b in backups_db.values()
        if b["owner_email"] == current_user["email"]
    ]


@router.post("/sync/start", response_model=SyncStatusResponse)
def start_sync(current_user: dict = Depends(get_current_user)):
    state = _get_sync_state(current_user["email"])
    state["status"] = "running"
    state["started_at"] = datetime.now(timezone.utc)
    state["stopped_at"] = None
    return SyncStatusResponse(**state)


@router.post("/sync/stop", response_model=SyncStatusResponse)
def stop_sync(current_user: dict = Depends(get_current_user)):
    state = _get_sync_state(current_user["email"])
    if state["status"] != "running":
        raise HTTPException(status_code=400, detail="Sync is not currently running")
    state["status"] = "stopped"
    state["stopped_at"] = datetime.now(timezone.utc)
    return SyncStatusResponse(**state)


@router.get("/sync/status", response_model=SyncStatusResponse)
def sync_status(current_user: dict = Depends(get_current_user)):
    state = _get_sync_state(current_user["email"])
    return SyncStatusResponse(**state)


@router.post("/replication/start", response_model=ReplicationStatusResponse)
def start_replication(current_user: dict = Depends(get_current_user)):
    replication_state["status"] = "running"
    replication_state["started_at"] = datetime.now(timezone.utc)
    replication_state["stopped_at"] = None
    return ReplicationStatusResponse(**replication_state)


@router.get("/replication/status", response_model=ReplicationStatusResponse)
def replication_status(current_user: dict = Depends(get_current_user)):
    return ReplicationStatusResponse(**replication_state)