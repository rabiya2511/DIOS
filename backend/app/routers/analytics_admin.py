"""
Analytics Administration router — health, logs, config, audit, backup.
Matches the Administration section of the Analytics APIs blueprint (5/5).

GET /analytics/health is intentionally public (no auth) since health
checks are typically called by uptime monitors without credentials.
All other endpoints require authentication.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends

from app.schemas.analytics_admin import (
    HealthResponse,
    LogEntry,
    ConfigUpdateRequest,
    ConfigResponse,
    AuditEntry,
    BackupCreateRequest,
    BackupResponse,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/analytics", tags=["Administration"])

_SERVER_STARTED_AT = datetime.now(timezone.utc)

# in-memory config (arbitrary key-value settings)
analytics_config_db: dict = {
    "retention_days": 90,
    "sampling_rate": 1.0,
}

# append-only audit log
analytics_audit_db: list[dict] = []

# backup records
analytics_backups_db: dict[str, dict] = {}

# synthetic log buffer, seeded with a few startup entries
analytics_logs_db: list[dict] = [
    {"level": "info", "message": "Analytics service started", "timestamp": _SERVER_STARTED_AT},
]


def _log_audit(action: str, detail: str, actor_email: str):
    analytics_audit_db.append(
        {
            "action": action,
            "detail": detail,
            "actor_email": actor_email,
            "timestamp": datetime.now(timezone.utc),
        }
    )


@router.get("/health", response_model=HealthResponse)
def get_health():
    """Public health check — no authentication required."""
    return HealthResponse(status="healthy", checked_at=datetime.now(timezone.utc))


@router.get("/logs", response_model=list[LogEntry])
def get_logs(current_user: dict = Depends(get_current_user)):
    return analytics_logs_db


@router.patch("/config", response_model=ConfigResponse)
def update_config(
    data: ConfigUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    analytics_config_db.update(data.settings)
    now = datetime.now(timezone.utc)
    _log_audit("config_updated", str(data.settings), current_user["email"])
    analytics_logs_db.append(
        {"level": "info", "message": f"Config updated by {current_user['email']}", "timestamp": now}
    )
    return ConfigResponse(settings=analytics_config_db, updated_at=now)


@router.get("/audit", response_model=list[AuditEntry])
def get_audit(current_user: dict = Depends(get_current_user)):
    return analytics_audit_db


@router.post("/backup", response_model=BackupResponse, status_code=201)
def create_backup(
    data: BackupCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    backup_id = str(uuid4())
    now = datetime.now(timezone.utc)
    analytics_backups_db[backup_id] = {
        "id": backup_id,
        "note": data.note,
        "status": "completed",
        "created_by_email": current_user["email"],
        "created_at": now,
    }
    _log_audit("backup_created", data.note or "no note", current_user["email"])
    analytics_logs_db.append(
        {"level": "info", "message": f"Backup {backup_id} created by {current_user['email']}", "timestamp": now}
    )
    return analytics_backups_db[backup_id]