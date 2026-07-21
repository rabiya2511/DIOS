"""
Membership router — invite/accept/reject flow, roles, removal.
Matches the Membership section of the User & Organization blueprint (6/6).
Distinct from organizations.py's direct-add invite (memberships_db) —
this uses a proper pending-invite flow via memberships_v2_db.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.membership import (
    MembershipInviteRequest,
    MembershipActionRequest,
    MembershipRoleUpdateRequest,
    MembershipOut,
)
from app.models.user import memberships_v2_db
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/members", tags=["Membership"])


@router.get("", response_model=list[MembershipOut])
def list_members(org_id: str, current_user: dict = Depends(get_current_user)):
    return [m for m in memberships_v2_db.values() if m["org_id"] == org_id]


@router.post("/invite", response_model=MembershipOut, status_code=201)
def invite_member(
    data: MembershipInviteRequest,
    current_user: dict = Depends(get_current_user),
):
    membership_id = str(uuid4())
    membership = {
        "id": membership_id,
        "org_id": data.org_id,
        "email": data.email,
        "role": data.role,
        "status": "pending",
        "invited_by": current_user["email"],
        "created_at": datetime.now(timezone.utc),
    }
    memberships_v2_db[membership_id] = membership
    return membership


@router.post("/accept", response_model=MembershipOut)
def accept_membership(
    data: MembershipActionRequest,
    current_user: dict = Depends(get_current_user),
):
    membership = memberships_v2_db.get(data.membership_id)
    if not membership:
        raise HTTPException(status_code=404, detail="Membership invite not found")
    if membership["email"] != current_user["email"]:
        raise HTTPException(status_code=403, detail="This invite is not addressed to you")
    if membership["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"Invite is already {membership['status']}")

    membership["status"] = "active"
    return membership


@router.post("/reject", response_model=MembershipOut)
def reject_membership(
    data: MembershipActionRequest,
    current_user: dict = Depends(get_current_user),
):
    membership = memberships_v2_db.get(data.membership_id)
    if not membership:
        raise HTTPException(status_code=404, detail="Membership invite not found")
    if membership["email"] != current_user["email"]:
        raise HTTPException(status_code=403, detail="This invite is not addressed to you")
    if membership["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"Invite is already {membership['status']}")

    membership["status"] = "rejected"
    return membership


@router.patch("/role", response_model=MembershipOut)
def update_member_role(
    data: MembershipRoleUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    membership = memberships_v2_db.get(data.membership_id)
    if not membership:
        raise HTTPException(status_code=404, detail="Membership not found")

    membership["role"] = data.role
    return membership


@router.delete("/{membership_id}", status_code=204)
def remove_membership(
    membership_id: str,
    current_user: dict = Depends(get_current_user),
):
    if membership_id not in memberships_v2_db:
        raise HTTPException(status_code=404, detail="Membership not found")
    del memberships_v2_db[membership_id]
    return None