"""
Deployment & Infrastructure router — Monitoring & Administration.
Matches the Monitoring & Administration section of the Deployment &
Infrastructure APIs blueprint (6/6). All endpoints require admin privileges.
Simulated — no real infrastructure layer exists yet.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.infra_admin import (
    InfraMetricsOut,
    InfraLogEntryOut,
    InfraAuditEntryOut,
    InfraConfigOut,
    InfraConfigUpdateRequest,
    InfraBackupOut,
    InfraRestoreRequest,
    InfraRestoreOut,
)
from app.models.user import infra_config_db, infra_backups_db, infra_logs_db, audit_logs_db
from app.core.security import get_current_admin

router = APIRouter(prefix="/api/v1/infra", tags=["Deployment & Infrastructure: Administration"])


@router.get("/metrics", response_model=InfraMetricsOut)
def get_infra_metrics(current_admin: dict = Depends(get_current_admin)):
    # STUB: simulated — no real deployment/node tracking yet.
    return InfraMetricsOut(
        total_deployments=0,
        healthy_nodes=1,
        total_nodes=1,
        uptime_percent=99.9,
    )


@router.get("/logs", response_model=list[InfraLogEntryOut])
def get_infra_logs(current_admin: dict = Depends(get_current_admin)):
    return infra_logs_db


@router.get("/audit", response_model=list[InfraAuditEntryOut])
def get_infra_audit(current_admin: dict = Depends(get_current_admin)):
    infra_actions = {"infra_backup", "infra_restore", "infra_config_update"}
    return sorted(
        [e for e in audit_logs_db if e["action"] in infra_actions],
        key=lambda x: x["timestamp"],
        reverse=True,
    )


@router.patch("/config", response_model=InfraConfigOut)
def update_infra_config(
    data: InfraConfigUpdateRequest,
    current_admin: dict = Depends(get_current_admin),
):
    updates = data.model_dump(exclude_unset=True)
    infra_config_db.update(updates)
    audit_logs_db.append({
        "actor_email": current_admin["email"],
        "action": "infra_config_update",
        "timestamp": datetime.now(timezone.utc),
    })
    return infra_config_db


@router.post("/backup", response_model=InfraBackupOut, status_code=201)
def create_infra_backup(current_admin: dict = Depends(get_current_admin)):
    backup_id = str(uuid4())
    now = datetime.now(timezone.utc)
    infra_backups_db.append({"id": backup_id, "created_at": now, "triggered_by": current_admin["email"]})
    audit_logs_db.append({
        "actor_email": current_admin["email"],
        "action": "infra_backup",
        "timestamp": now,
    })
    return InfraBackupOut(id=backup_id, message="Infrastructure backup created successfully.", created_at=now)


@router.post("/restore", response_model=InfraRestoreOut)
def restore_infra_backup(
    data: InfraRestoreRequest,
    current_admin: dict = Depends(get_current_admin),
):
    backup = next((b for b in infra_backups_db if b["id"] == data.backup_id), None)
    if not backup:
        raise HTTPException(status_code=404, detail="Backup not found")

    now = datetime.now(timezone.utc)
    audit_logs_db.append({
        "actor_email": current_admin["email"],
        "action": "infra_restore",
        "timestamp": now,
    })
    return InfraRestoreOut(
        backup_id=data.backup_id,
        message="Infrastructure restored successfully (simulated).",
        restored_at=now,
    )