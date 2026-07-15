"""
Admin router — Backup & Monitoring.
Matches section 6 of the Administration blueprint (6/6).
All endpoints require admin privileges.
"""

import time
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.admin_backup import (
    BackupResponse,
    RestoreRequest,
    RestoreResponse,
    MetricsOut,
    LogEntryOut,
    AlertOut,
    AdminSettingsOut,
    AdminSettingsUpdateRequest,
)
from app.models.user import (
    backups_db,
    app_logs_db,
    alerts_db,
    admin_settings_db,
    users_db,
    organizations_db,
)
from app.core.security import get_current_admin

router = APIRouter(prefix="/api/v1/admin", tags=["Admin: Backup & Monitoring"])

_start_time = time.time()


@router.post("/backup", response_model=BackupResponse, status_code=201)
def create_backup(current_admin: dict = Depends(get_current_admin)):
    backup_id = str(uuid4())
    now = datetime.now(timezone.utc)
    backups_db.append({"id": backup_id, "created_at": now, "triggered_by": current_admin["email"]})
    return BackupResponse(id=backup_id, message="Backup created successfully.", created_at=now)


@router.post("/restore", response_model=RestoreResponse)
def restore_backup(
    data: RestoreRequest,
    current_admin: dict = Depends(get_current_admin),
):
    backup = next((b for b in backups_db if b["id"] == data.backup_id), None)
    if not backup:
        raise HTTPException(status_code=404, detail="Backup not found")

    now = datetime.now(timezone.utc)
    return RestoreResponse(
        message="Restore completed successfully (simulated).",
        backup_id=data.backup_id,
        restored_at=now,
    )


@router.get("/metrics", response_model=MetricsOut)
def get_metrics(current_admin: dict = Depends(get_current_admin)):
    uptime = time.time() - _start_time
    return MetricsOut(
        total_users=len(users_db),
        total_organizations=len(organizations_db),
        total_api_keys=0,  # TODO: wire to api_keys_db once accessible here
        uptime_seconds=round(uptime, 2),
    )


@router.get("/logs", response_model=list[LogEntryOut])
def get_logs(current_admin: dict = Depends(get_current_admin)):
    return app_logs_db


@router.get("/alerts", response_model=list[AlertOut])
def get_alerts(current_admin: dict = Depends(get_current_admin)):
    return alerts_db


@router.patch("/settings", response_model=AdminSettingsOut)
def update_settings(
    data: AdminSettingsUpdateRequest,
    current_admin: dict = Depends(get_current_admin),
):
    updates = data.model_dump(exclude_unset=True)
    admin_settings_db.update(updates)
    return admin_settings_db