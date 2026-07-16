"""
Audit & Compliance router — the final section of the Authorization blueprint (10/10).
Tracks authorization-specific audit entries, reviews, and archival, separate
from the general-purpose audit log built earlier.
"""

import csv
import io
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.schemas.authz_audit import (
    AuthzAuditEntryOut,
    AuthzLogEntryOut,
    AuthzReportOut,
    AuthzViolationOut,
    ReviewRequest,
    ReviewOut,
    ArchiveResponse,
)
from app.models.user import authz_audit_db, authz_violations_db, authz_reviews_db, audit_logs_db
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/authorization", tags=["Audit & Compliance"])


def _log_authz_action(actor_email: str, action: str, resource_type: str = None, resource_id: str = None):
    authz_audit_db.append({
        "id": str(uuid4()),
        "actor_email": actor_email,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "timestamp": datetime.now(timezone.utc),
        "archived": False,
    })


@router.get("/audit", response_model=list[AuthzAuditEntryOut])
def get_authz_audit(current_user: dict = Depends(get_current_user)):
    return sorted(authz_audit_db, key=lambda x: x["timestamp"], reverse=True)


@router.get("/events", response_model=list[AuthzAuditEntryOut])
def get_authz_events(current_user: dict = Depends(get_current_user)):
    return sorted(authz_audit_db, key=lambda x: x["timestamp"], reverse=True)


@router.get("/logs", response_model=list[AuthzLogEntryOut])
def get_authz_logs(current_user: dict = Depends(get_current_user)):
    return sorted(audit_logs_db, key=lambda x: x["timestamp"], reverse=True)


@router.get("/reports", response_model=AuthzReportOut)
def get_authz_reports(current_user: dict = Depends(get_current_user)):
    return AuthzReportOut(
        generated_at=datetime.now(timezone.utc),
        total_audit_entries=len(authz_audit_db),
        total_login_events=len(audit_logs_db),
        total_reviews=len(authz_reviews_db),
        total_violations=len(authz_violations_db),
    )


@router.post("/export")
def export_authz_audit(current_user: dict = Depends(get_current_user)):
    _log_authz_action(current_user["email"], "export")

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=["id", "actor_email", "action", "resource_type", "resource_id", "timestamp"])
    writer.writeheader()
    for entry in authz_audit_db:
        writer.writerow({
            "id": entry["id"],
            "actor_email": entry["actor_email"],
            "action": entry["action"],
            "resource_type": entry["resource_type"],
            "resource_id": entry["resource_id"],
            "timestamp": entry["timestamp"].isoformat(),
        })
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=authorization_audit_export.csv"},
    )


@router.get("/violations", response_model=list[AuthzViolationOut])
def get_violations(current_user: dict = Depends(get_current_user)):
    return sorted(authz_violations_db, key=lambda x: x["timestamp"], reverse=True)


@router.post("/review", response_model=ReviewOut, status_code=201)
def create_review(
    data: ReviewRequest,
    current_user: dict = Depends(get_current_user),
):
    review = {
        "id": str(uuid4()),
        "reviewer_email": current_user["email"],
        "note": data.note,
        "timestamp": datetime.now(timezone.utc),
    }
    authz_reviews_db.append(review)
    _log_authz_action(current_user["email"], "review")
    return review


@router.get("/history", response_model=list[AuthzAuditEntryOut])
def get_authz_history(current_user: dict = Depends(get_current_user)):
    return sorted(authz_audit_db, key=lambda x: x["timestamp"], reverse=True)


@router.get("/changes", response_model=list[AuthzAuditEntryOut])
def get_authz_changes(current_user: dict = Depends(get_current_user)):
    change_actions = {"review", "archive", "export"}
    changes = [e for e in authz_audit_db if e["action"] in change_actions]
    return sorted(changes, key=lambda x: x["timestamp"], reverse=True)


@router.post("/archive", response_model=ArchiveResponse)
def archive_authz_entries(current_user: dict = Depends(get_current_user)):
    count = 0
    for entry in authz_audit_db:
        if not entry["archived"]:
            entry["archived"] = True
            count += 1
    now = datetime.now(timezone.utc)
    _log_authz_action(current_user["email"], "archive")
    return ArchiveResponse(archived_count=count, timestamp=now)