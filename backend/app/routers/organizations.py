"""
Organizations router — create, list, invite, member-role, member, members.
Matches the Organizations section of the Auth blueprint (6/6).
STUBBED: invite adds the member directly instead of sending a real
email/invite-token flow.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.organizations import (
    OrganizationCreateRequest,
    OrganizationResponse,
    OrganizationUpdateRequest,
    OrganizationInviteRequest,
    MemberRoleUpdateRequest,
    MemberRemoveRequest,
    MembersResponse,
    MemberItem,
    ArchiveRequest,
    RestoreRequest,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/organizations", tags=["Organizations"])

# org_id -> {id, name, owner_email, created_at}
organizations_db: dict[str, dict] = {}

# org_id -> {email: role}
memberships_db: dict[str, dict[str, str]] = {}


def _get_org_or_404(org_id: str) -> dict:
    org = organizations_db.get(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


def _require_admin(org_id: str, email: str):
    role = memberships_db.get(org_id, {}).get(email)
    if role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Requires owner or admin role")


def _require_owner(org_id: str, email: str):
    role = memberships_db.get(org_id, {}).get(email)
    if role != "owner":
        raise HTTPException(status_code=403, detail="Requires owner role")


def _require_member(org_id: str, email: str):
    if email not in memberships_db.get(org_id, {}):
        raise HTTPException(status_code=403, detail="Not a member of this organization")


def _org_response(org: dict, role: str) -> OrganizationResponse:
    org.setdefault("archived", False)
    return OrganizationResponse(
        id=org["id"],
        name=org["name"],
        owner_email=org["owner_email"],
        role=role,
        created_at=org["created_at"],
    )


@router.post("", response_model=OrganizationResponse, status_code=201)
def create_organization(
    data: OrganizationCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    org_id = str(uuid4())
    now = datetime.now(timezone.utc)
    organizations_db[org_id] = {
        "id": org_id,
        "name": data.name,
        "owner_email": current_user["email"],
        "created_at": now,
    }
    memberships_db[org_id] = {current_user["email"]: "owner"}
    return OrganizationResponse(
        id=org_id,
        name=data.name,
        owner_email=current_user["email"],
        role="owner",
        created_at=now,
    )


@router.get("", response_model=list[OrganizationResponse])
def list_organizations(current_user: dict = Depends(get_current_user)):
    result = []
    for org_id, org in organizations_db.items():
        role = memberships_db.get(org_id, {}).get(current_user["email"])
        if role:
            result.append(
                OrganizationResponse(
                    id=org["id"],
                    name=org["name"],
                    owner_email=org["owner_email"],
                    role=role,
                    created_at=org["created_at"],
                )
            )
    return result


@router.post("/invite", status_code=201)
def invite_member(
    data: OrganizationInviteRequest,
    current_user: dict = Depends(get_current_user),
):
    _get_org_or_404(data.org_id)
    _require_admin(data.org_id, current_user["email"])

    # STUB: real version emails an invite link/token; here we add directly.
    memberships_db[data.org_id][data.email] = data.role
    return {"detail": f"{data.email} added to organization as {data.role}"}


@router.patch("/member-role", status_code=204)
def update_member_role(
    data: MemberRoleUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    _get_org_or_404(data.org_id)
    _require_admin(data.org_id, current_user["email"])

    members = memberships_db[data.org_id]
    if data.email not in members:
        raise HTTPException(status_code=404, detail="Member not found in organization")

    members[data.email] = data.role
    return None


@router.delete("/member", status_code=204)
def remove_member(
    data: MemberRemoveRequest,
    current_user: dict = Depends(get_current_user),
):
    _get_org_or_404(data.org_id)
    _require_admin(data.org_id, current_user["email"])

    members = memberships_db[data.org_id]
    if data.email not in members:
        raise HTTPException(status_code=404, detail="Member not found in organization")

    if members[data.email] == "owner":
        owners = [e for e, r in members.items() if r == "owner"]
        if len(owners) <= 1:
            raise HTTPException(status_code=400, detail="Cannot remove the last owner")

    del members[data.email]
    return None


@router.get("/members", response_model=MembersResponse)
def list_members(org_id: str, current_user: dict = Depends(get_current_user)):
    _get_org_or_404(org_id)
    members = memberships_db.get(org_id, {})
    if current_user["email"] not in members:
        raise HTTPException(status_code=403, detail="Not a member of this organization")

    return MembersResponse(
        org_id=org_id,
        members=[MemberItem(email=e, role=r) for e, r in members.items()],
    )


# NOTE: /archive and /restore must stay registered before the /{org_id}
# catch-all below, or FastAPI will match them as org_id="archive" /
# org_id="restore" instead.
@router.post("/archive", response_model=OrganizationResponse)
def archive_organization(
    data: ArchiveRequest,
    current_user: dict = Depends(get_current_user),
):
    org = _get_org_or_404(data.org_id)
    _require_admin(data.org_id, current_user["email"])
    org["archived"] = True
    role = memberships_db[data.org_id][current_user["email"]]
    return _org_response(org, role)


@router.post("/restore", response_model=OrganizationResponse)
def restore_organization(
    data: RestoreRequest,
    current_user: dict = Depends(get_current_user),
):
    org = _get_org_or_404(data.org_id)
    _require_admin(data.org_id, current_user["email"])
    org["archived"] = False
    role = memberships_db[data.org_id][current_user["email"]]
    return _org_response(org, role)


# /{org_id} catch-all — must come after all literal sibling paths above
# (/invite, /member-role, /member, /members, /archive, /restore).
@router.get("/{org_id}", response_model=OrganizationResponse)
def get_organization(org_id: str, current_user: dict = Depends(get_current_user)):
    org = _get_org_or_404(org_id)
    _require_member(org_id, current_user["email"])
    role = memberships_db[org_id][current_user["email"]]
    return _org_response(org, role)


@router.patch("/{org_id}", response_model=OrganizationResponse)
def update_organization(
    org_id: str,
    data: OrganizationUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    org = _get_org_or_404(org_id)
    _require_admin(org_id, current_user["email"])
    if data.name is not None:
        org["name"] = data.name
    role = memberships_db[org_id][current_user["email"]]
    return _org_response(org, role)


@router.delete("/{org_id}", status_code=204)
def delete_organization(org_id: str, current_user: dict = Depends(get_current_user)):
    _get_org_or_404(org_id)
    _require_owner(org_id, current_user["email"])
    del organizations_db[org_id]
    memberships_db.pop(org_id, None)
    return None 