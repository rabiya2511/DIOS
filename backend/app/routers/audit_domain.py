"""
Audit router — domain-scoped views (users, organizations, roles) plus export.
Matches the Audit section of the User & Organization blueprint (4/4).
Filters the shared audit_logs_db by action-name prefix/category; as more
actions get logged into audit_logs_db elsewhere, these views populate
automatically without needing separate storage.

NOTE: mounted at /export-csv instead of /export to avoid colliding with
the existing GET /audit/export in security.py (plain JSON export).
"""

import csv
import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.schemas.audit_domain import DomainAuditEntryOut
from app.models.user import audit_logs_db
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/audit", tags=["Audit"])

USER_ACTIONS = {"login", "register", "password_change", "profile_update", "suspend", "activate", "lock", "unlock"}
ORG_ACTIONS = {"org_create", "org_update", "org_archive", "org_restore", "org_delete"}
ROLE_ACTIONS = {"role_create", "role_update", "role_delete", "role_assign", "role_unassign"}


def _filter_by_category(categories: set[str]) -> list[dict]:
    return sorted(
        [e for e in audit_logs_db if e["action"] in categories],
        key=lambda x: x["timestamp"],
        reverse=True,
    )


@router.get("/users", response_model=list[DomainAuditEntryOut])
def get_user_audit(current_user: dict = Depends(get_current_user)):
    return _filter_by_category(USER_ACTIONS)


@router.get("/organizations", response_model=list[DomainAuditEntryOut])
def get_organization_audit(current_user: dict = Depends(get_current_user)):
    return _filter_by_category(ORG_ACTIONS)


@router.get("/roles", response_model=list[DomainAuditEntryOut])
def get_role_audit(current_user: dict = Depends(get_current_user)):
    return _filter_by_category(ROLE_ACTIONS)


@router.get("/export-csv")
def export_audit(current_user: dict = Depends(get_current_user)):
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=["actor_email", "action", "timestamp"])
    writer.writeheader()
    for entry in sorted(audit_logs_db, key=lambda x: x["timestamp"], reverse=True):
        writer.writerow({
            "actor_email": entry["actor_email"],
            "action": entry["action"],
            "timestamp": entry["timestamp"].isoformat(),
        })
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_export.csv"},
    )