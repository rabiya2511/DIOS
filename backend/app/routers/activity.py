"""
Activity router — activity feed, usage, login history, audit, notifications, exports.
Matches the Activity section of the User Management blueprint (8/8).
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends

from app.schemas.activity import (
    ActivityEntryOut,
    UsageOut,
    LoginHistoryEntryOut,
    AuditEntryOut,
    NotificationOut,
    ExportRequest,
    ExportOut,
)
from app.models.user import (
    login_history_db,
    audit_logs_db,
    notifications_db,
    exports_db,
    users_db,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1", tags=["Activity"])


def _build_activity_feed(email: str) -> list[dict]:
    entries = []
    for entry in login_history_db.get(email, []):
        entries.append({
            "type": "login",
            "detail": "Successful login" if entry["success"] else "Failed login attempt",
            "timestamp": entry["timestamp"],
        })
    for entry in audit_logs_db:
        if entry["actor_email"] == email:
            entries.append({
                "type": "audit",
                "detail": entry["action"],
                "timestamp": entry["timestamp"],
            })
    entries.sort(key=lambda x: x["timestamp"], reverse=True)
    return entries


@router.get("/activity", response_model=list[ActivityEntryOut])
def get_my_activity(current_user: dict = Depends(get_current_user)):
    return _build_activity_feed(current_user["email"])


@router.get("/activity/{user_id}", response_model=list[ActivityEntryOut])
def get_user_activity(user_id: str, current_user: dict = Depends(get_current_user)):
    target = next((u for u in users_db.values() if u["id"] == user_id), None)
    if not target:
        return []
    return _build_activity_feed(target["email"])


@router.get("/usage", response_model=UsageOut)
def get_usage(current_user: dict = Depends(get_current_user)):
    email = current_user["email"]
    logins = len(login_history_db.get(email, []))
    audit_count = sum(1 for e in audit_logs_db if e["actor_email"] == email)
    age_days = (datetime.now(timezone.utc) - current_user["created_at"]).days
    return UsageOut(total_logins=logins, total_audit_actions=audit_count, account_age_days=age_days)


@router.get("/login-history", response_model=list[LoginHistoryEntryOut])
def get_login_history(current_user: dict = Depends(get_current_user)):
    return login_history_db.get(current_user["email"], [])


@router.get("/audit", response_model=list[AuditEntryOut])
def get_audit(current_user: dict = Depends(get_current_user)):
    email = current_user["email"]
    return [e for e in audit_logs_db if e["actor_email"] == email]


@router.get("/notifications", response_model=list[NotificationOut])
def get_notifications(current_user: dict = Depends(get_current_user)):
    email = current_user["email"]
    if email not in notifications_db:
        now = datetime.now(timezone.utc)
        notifications_db[email] = [
            {"id": str(uuid4()), "message": "Welcome to DIOS!", "read": False, "created_at": now},
        ]
    return notifications_db[email]


@router.get("/exports", response_model=list[ExportOut])
def list_exports(current_user: dict = Depends(get_current_user)):
    return exports_db.get(current_user["email"], [])


@router.post("/exports", response_model=ExportOut, status_code=201)
def create_export(
    data: ExportRequest,
    current_user: dict = Depends(get_current_user),
):
    email = current_user["email"]
    export = {
        "id": str(uuid4()),
        "type": data.export_type,
        "status": "completed",  # simulated — real version would be "pending" then processed async
        "created_at": datetime.now(timezone.utc),
    }
    exports_db.setdefault(email, []).append(export)
    return export