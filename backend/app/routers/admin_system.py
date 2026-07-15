"""
Admin router — System Operations.
Matches section 4 of the Administration blueprint (6/6).
All endpoints require admin privileges.
Most operations here are simulated (no real cache/search-index backing yet).
"""

import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.schemas.admin_system import (
    SystemOperationResponse,
    SystemHealthOut,
    SystemVersionOut,
    MaintenanceRequest,
    MaintenanceResponse,
)
from app.models.user import system_ops_log_db, platform_config_db
from app.core.security import get_current_admin

router = APIRouter(prefix="/api/v1/admin", tags=["Admin: System Operations"])

_start_time = time.time()


def _log_operation(operation: str, admin_email: str) -> datetime:
    now = datetime.now(timezone.utc)
    system_ops_log_db.append({
        "operation": operation,
        "timestamp": now,
        "triggered_by": admin_email,
    })
    return now


@router.post("/cache/clear", response_model=SystemOperationResponse)
def clear_cache(current_admin: dict = Depends(get_current_admin)):
    ts = _log_operation("cache_clear", current_admin["email"])
    return SystemOperationResponse(message="Cache cleared successfully.", timestamp=ts)


@router.post("/reindex", response_model=SystemOperationResponse)
def reindex(current_admin: dict = Depends(get_current_admin)):
    ts = _log_operation("reindex", current_admin["email"])
    return SystemOperationResponse(message="Reindex triggered successfully.", timestamp=ts)


@router.post("/reload", response_model=SystemOperationResponse)
def reload_config(current_admin: dict = Depends(get_current_admin)):
    ts = _log_operation("reload", current_admin["email"])
    return SystemOperationResponse(message="Configuration reloaded successfully.", timestamp=ts)


@router.get("/system/health", response_model=SystemHealthOut)
def system_health(current_admin: dict = Depends(get_current_admin)):
    uptime = time.time() - _start_time
    return SystemHealthOut(status="healthy", uptime_seconds=round(uptime, 2), database="in-memory")


@router.get("/system/version", response_model=SystemVersionOut)
def system_version(current_admin: dict = Depends(get_current_admin)):
    return SystemVersionOut(api_version="0.1.0", build="dev", environment="development")


@router.post("/maintenance", response_model=MaintenanceResponse)
def set_maintenance(
    data: MaintenanceRequest,
    current_admin: dict = Depends(get_current_admin),
):
    platform_config_db["maintenance_mode"] = data.enabled
    _log_operation("maintenance_toggle", current_admin["email"])
    return MaintenanceResponse(maintenance_mode=data.enabled, message=data.message)