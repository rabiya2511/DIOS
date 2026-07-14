"""
Security & Audit router — security events, login history, audit logs, audit export.
Matches the Security & Audit section of the Auth blueprint (4/4).
"""

import csv
import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.schemas.security import SecurityEventOut, LoginHistoryOut, AuditLogOut
from app.models.user import security_events_db, login_history_db, audit_logs_db
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1", tags=["Security & Audit"])


@router.get("/security/events", response_model=list[SecurityEventOut])
def get_security_events(current_user: dict = Depends(get_current_user)):
    email = current_user["email"]
    return security_events_db.get(email, [])


@router.get("/security/login-history", response_model=list[LoginHistoryOut])
def get_login_history(current_user: dict = Depends(get_current_user)):
    email = current_user["email"]
    return login_history_db.get(email, [])


@router.get("/audit/logs", response_model=list[AuditLogOut])
def get_audit_logs(current_user: dict = Depends(get_current_user)):
    email = current_user["email"]
    return [log for log in audit_logs_db if log["actor_email"] == email]


@router.get("/audit/export")
def export_audit_logs(current_user: dict = Depends(get_current_user)):
    email = current_user["email"]
    logs = [log for log in audit_logs_db if log["actor_email"] == email]

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=["actor_email", "action", "timestamp"])
    writer.writeheader()
    for log in logs:
        writer.writerow({
            "actor_email": log["actor_email"],
            "action": log["action"],
            "timestamp": log["timestamp"].isoformat(),
        })
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_log_export.csv"},
    )