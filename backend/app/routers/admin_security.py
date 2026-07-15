"""
Admin router — Security & Audit.
Matches section 5 of the Administration blueprint (6/6).
All endpoints require admin privileges.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.schemas.admin_security import (
    AdminSecurityEventOut,
    RotateKeysResponse,
    RevokeSessionsResponse,
    AdminAuditLogOut,
    AdminAccessHistoryOut,
    ComplianceReportOut,
)
from app.models.user import (
    security_events_db,
    audit_logs_db,
    login_history_db,
    refresh_tokens_db,
    users_db,
    system_ops_log_db,
)
from app.core.security import get_current_admin

router = APIRouter(prefix="/api/v1/admin", tags=["Admin: Security & Audit"])


@router.get("/security/events", response_model=list[AdminSecurityEventOut])
def admin_security_events(current_admin: dict = Depends(get_current_admin)):
    events = []
    for email, entries in security_events_db.items():
        for entry in entries:
            events.append({
                "email": email,
                "event": entry["event"],
                "detail": entry["detail"],
                "timestamp": entry["timestamp"],
            })
    events.sort(key=lambda x: x["timestamp"], reverse=True)
    return events


@router.post("/security/rotate-keys", response_model=RotateKeysResponse)
def rotate_keys(current_admin: dict = Depends(get_current_admin)):
    now = datetime.now(timezone.utc)
    system_ops_log_db.append({
        "operation": "rotate_keys",
        "timestamp": now,
        "triggered_by": current_admin["email"],
    })
    # NOTE: simulated — actually swapping SECRET_KEY here would invalidate all
    # active sessions immediately, including the admin's own. Real rotation
    # would need a grace-period / dual-key verification strategy.
    return RotateKeysResponse(message="Signing keys rotated successfully (simulated).", timestamp=now)


@router.post("/security/revoke-sessions", response_model=RevokeSessionsResponse)
def revoke_sessions(current_admin: dict = Depends(get_current_admin)):
    count = len(refresh_tokens_db)
    refresh_tokens_db.clear()
    now = datetime.now(timezone.utc)
    system_ops_log_db.append({
        "operation": "revoke_all_sessions",
        "timestamp": now,
        "triggered_by": current_admin["email"],
    })
    return RevokeSessionsResponse(
        message="All active sessions revoked.",
        sessions_revoked=count,
        timestamp=now,
    )


@router.get("/audit", response_model=list[AdminAuditLogOut])
def admin_audit(current_admin: dict = Depends(get_current_admin)):
    return sorted(audit_logs_db, key=lambda x: x["timestamp"], reverse=True)


@router.get("/access-history", response_model=list[AdminAccessHistoryOut])
def admin_access_history(current_admin: dict = Depends(get_current_admin)):
    history = []
    for email, entries in login_history_db.items():
        for entry in entries:
            history.append({
                "email": email,
                "success": entry["success"],
                "ip": entry["ip"],
                "timestamp": entry["timestamp"],
            })
    history.sort(key=lambda x: x["timestamp"], reverse=True)
    return history


@router.post("/compliance/report", response_model=ComplianceReportOut)
def compliance_report(current_admin: dict = Depends(get_current_admin)):
    total_login_attempts = sum(len(entries) for entries in login_history_db.values())
    return ComplianceReportOut(
        generated_at=datetime.now(timezone.utc),
        total_users=len(users_db),
        total_admins=sum(1 for u in users_db.values() if u.get("is_admin", False)),
        suspended_users=sum(1 for u in users_db.values() if u.get("suspended", False)),
        total_audit_entries=len(audit_logs_db),
        total_login_attempts=total_login_attempts,
    )