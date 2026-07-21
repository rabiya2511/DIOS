"""
Organization Authorization router — path-scoped member management,
org-level permission grants, audit log, access summary, transfer-owner.
Matches the Organization Authorization section of the Authorization
APIs blueprint (10/10). Reuses organizations_db and memberships_db from
the existing organizations.py router rather than duplicating org data.
Also feeds the shared audit_logs_db so GET /audit/organizations has real data.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.org_authorization import (
    OrgMemberAddRequest,
    OrgMemberResponse,
    OrgMemberRoleUpdateRequest,
    OrgPermissionGrantRequest,
    OrgPermissionResponse,
    OrgAuditEntry,
    OrgAccessResponse,
    OrgTransferOwnerRequest,
)
from app.routers.organizations import organizations_db, memberships_db
from app.routers.permissions import permissions_db
from app.models.user import audit_logs_db
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/organizations", tags=["Organization Authorization"])

# org_id -> {permission_key: {"granted_at": datetime}}
org_permissions_db: dict[str, dict[str, dict]] = {}

# append-only audit log
org_audit_db: list[dict] = []

_ORG_ACTION_MAP = {
    "member_added": "org_update",
    "member_removed": "org_update",
    "member_role_updated": "org_update",
    "permission_granted": "org_update",
    "permission_revoked": "org_update",
    "ownership_transferred": "org_update",
}


def _get_org_or_404(org_id: str) -> dict:
    org = organizations_db.get(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


def _require_admin(org_id: str, email: str):
    role = memberships_db.get(org_id, {}).get(email)
    if role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Requires owner or admin role")


def _log_audit(org_id: str, action: str, actor_email: str, detail: str):
    org_audit_db.append(
        {
            "org_id": org_id,
            "action": action,
            "actor_email": actor_email,
            "detail": detail,
            "timestamp": datetime.now(timezone.utc),
        }
    )
    # also feed the shared cross-domain audit log used by GET /audit/organizations
    audit_logs_db.append(
        {
            "actor_email": actor_email,
            "action": _ORG_ACTION_MAP.get(action, "org_update"),
            "timestamp": datetime.now(timezone.utc),
        }
    )


@router.get("/{id}/members", response_model=list[OrgMemberResponse])
def get_members(id: str, current_user: dict = Depends(get_current_user)):
    _get_org_or_404(id)
    members = memberships_db.get(id, {})
    if current_user["email"] not in members:
        raise HTTPException(status_code=403, detail="Not a member of this organization")
    return [OrgMemberResponse(email=e, role=r) for e, r in members.items()]


@router.post("/{id}/members", response_model=OrgMemberResponse, status_code=201)
def add_member(
    id: str,
    data: OrgMemberAddRequest,
    current_user: dict = Depends(get_current_user),
):
    _get_org_or_404(id)
    _require_admin(id, current_user["email"])
    memberships_db[id][data.email] = data.role
    _log_audit(id, "member_added", current_user["email"], f"{data.email} added as {data.role}")
    return OrgMemberResponse(email=data.email, role=data.role)


@router.delete("/{id}/members/{userId}", status_code=204)
def remove_member(
    id: str,
    userId: str,
    current_user: dict = Depends(get_current_user),
):
    _get_org_or_404(id)
    _require_admin(id, current_user["email"])
    members = memberships_db.get(id, {})
    if userId not in members:
        raise HTTPException(status_code=404, detail="Member not found in organization")

    if members[userId] == "owner":
        owners = [e for e, r in members.items() if r == "owner"]
        if len(owners) <= 1:
            raise HTTPException(status_code=400, detail="Cannot remove the last owner")

    del members[userId]
    _log_audit(id, "member_removed", current_user["email"], f"{userId} removed")
    return None


@router.patch("/{id}/members/{userId}/role", response_model=OrgMemberResponse)
def update_member_role(
    id: str,
    userId: str,
    data: OrgMemberRoleUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    _get_org_or_404(id)
    _require_admin(id, current_user["email"])
    members = memberships_db.get(id, {})
    if userId not in members:
        raise HTTPException(status_code=404, detail="Member not found in organization")

    old_role = members[userId]
    members[userId] = data.role
    _log_audit(id, "member_role_updated", current_user["email"], f"{userId}: {old_role} -> {data.role}")
    return OrgMemberResponse(email=userId, role=data.role)


@router.get("/{id}/permissions", response_model=list[OrgPermissionResponse])
def get_org_permissions(id: str, current_user: dict = Depends(get_current_user)):
    _get_org_or_404(id)
    grants = org_permissions_db.get(id, {})
    return [OrgPermissionResponse(key=k, granted_at=v["granted_at"]) for k, v in grants.items()]


@router.post("/{id}/permissions", response_model=OrgPermissionResponse, status_code=201)
def grant_org_permission(
    id: str,
    data: OrgPermissionGrantRequest,
    current_user: dict = Depends(get_current_user),
):
    _get_org_or_404(id)
    _require_admin(id, current_user["email"])

    if not any(p["key"] == data.key for p in permissions_db.values()):
        raise HTTPException(status_code=404, detail=f"Permission key '{data.key}' does not exist")

    now = datetime.now(timezone.utc)
    org_permissions_db.setdefault(id, {})[data.key] = {"granted_at": now}
    _log_audit(id, "permission_granted", current_user["email"], f"granted '{data.key}'")
    return OrgPermissionResponse(key=data.key, granted_at=now)


@router.delete("/{id}/permissions/{permissionId}", status_code=204)
def revoke_org_permission(
    id: str,
    permissionId: str,
    current_user: dict = Depends(get_current_user),
):
    _get_org_or_404(id)
    _require_admin(id, current_user["email"])

    grants = org_permissions_db.get(id, {})
    if permissionId not in grants:
        raise HTTPException(status_code=404, detail="This permission is not granted to this organization")

    del grants[permissionId]
    _log_audit(id, "permission_revoked", current_user["email"], f"revoked '{permissionId}'")
    return None


@router.get("/{id}/audit", response_model=list[OrgAuditEntry])
def get_org_audit(id: str, current_user: dict = Depends(get_current_user)):
    _get_org_or_404(id)
    _require_admin(id, current_user["email"])
    return [OrgAuditEntry(**entry) for entry in org_audit_db if entry["org_id"] == id]


@router.get("/{id}/access", response_model=OrgAccessResponse)
def get_org_access(id: str, current_user: dict = Depends(get_current_user)):
    _get_org_or_404(id)
    members = memberships_db.get(id, {})
    if current_user["email"] not in members:
        raise HTTPException(status_code=403, detail="Not a member of this organization")

    grants = org_permissions_db.get(id, {})
    return OrgAccessResponse(
        org_id=id,
        members=[OrgMemberResponse(email=e, role=r) for e, r in members.items()],
        granted_permissions=sorted(grants.keys()),
    )


@router.post("/{id}/transfer-owner", status_code=204)
def transfer_owner(
    id: str,
    data: OrgTransferOwnerRequest,
    current_user: dict = Depends(get_current_user),
):
    _get_org_or_404(id)
    _require_admin(id, current_user["email"])
    members = memberships_db.get(id, {})
    if data.new_owner_email not in members:
        raise HTTPException(status_code=404, detail="New owner must already be a member of this organization")

    current_owners = [e for e, r in members.items() if r == "owner"]
    for owner_email in current_owners:
        members[owner_email] = "admin"
    members[data.new_owner_email] = "owner"
    organizations_db[id]["owner_email"] = data.new_owner_email

    _log_audit(
        id,
        "ownership_transferred",
        current_user["email"],
        f"ownership transferred to {data.new_owner_email}",
    )
    return None