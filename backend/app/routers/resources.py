"""
Resource Authorization router — share, permissions, ownership, lock, inherit, revoke-all.
Matches the Resource Authorization section of the Authorization blueprint (10/10).
Resources are generic — identified by resource_id, tracked only for authorization purposes.
"""

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.resources import (
    ResourceShareRequest,
    ResourceShareOut,
    ResourcePermissionsOut,
    ResourcePermissionsUpdateRequest,
    ResourceOwnerRequest,
    ResourceAccessOut,
    ResourceLockResponse,
    ResourceInheritRequest,
    ResourceRevokeAllResponse,
)
from app.models.user import resource_owners_db, resource_shares_db, resource_locks_db
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/resources", tags=["Resource Authorization"])


def _require_owner_or_claim(resource_id: str, current_user: dict) -> str:
    """If the resource has no owner yet, the caller claims ownership. Otherwise, require ownership."""
    owner = resource_owners_db.get(resource_id)
    if owner is None:
        resource_owners_db[resource_id] = current_user["email"]
        return current_user["email"]
    if owner != current_user["email"]:
        raise HTTPException(status_code=403, detail="Only the resource owner can perform this action")
    return owner


def _require_unlocked(resource_id: str):
    if resource_locks_db.get(resource_id, False):
        raise HTTPException(status_code=423, detail="Resource is locked")


@router.post("/share", response_model=ResourceShareOut, status_code=201)
def share_resource(
    data: ResourceShareRequest,
    current_user: dict = Depends(get_current_user),
):
    _require_owner_or_claim(data.resource_id, current_user)
    _require_unlocked(data.resource_id)

    share_id = str(uuid4())
    share = {"id": share_id, "resource_id": data.resource_id, "email": data.email, "permission": data.permission}
    resource_shares_db.setdefault(data.resource_id, []).append(share)
    return share


@router.delete("/share/{share_id}", status_code=204)
def unshare_resource(
    share_id: str,
    current_user: dict = Depends(get_current_user),
):
    for resource_id, shares in resource_shares_db.items():
        match = next((s for s in shares if s["id"] == share_id), None)
        if match:
            if resource_owners_db.get(resource_id) != current_user["email"]:
                raise HTTPException(status_code=403, detail="Only the resource owner can perform this action")
            _require_unlocked(resource_id)
            shares.remove(match)
            return None
    raise HTTPException(status_code=404, detail="Share not found")


@router.get("/{resource_id}/permissions", response_model=ResourcePermissionsOut)
def get_resource_permissions(
    resource_id: str,
    current_user: dict = Depends(get_current_user),
):
    return ResourcePermissionsOut(
        resource_id=resource_id,
        owner_email=resource_owners_db.get(resource_id),
        shares=resource_shares_db.get(resource_id, []),
    )


@router.patch("/{resource_id}/permissions", response_model=ResourceShareOut)
def update_resource_permission(
    resource_id: str,
    data: ResourcePermissionsUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    if resource_owners_db.get(resource_id) != current_user["email"]:
        raise HTTPException(status_code=403, detail="Only the resource owner can perform this action")
    _require_unlocked(resource_id)

    shares = resource_shares_db.get(resource_id, [])
    match = next((s for s in shares if s["email"] == data.email), None)
    if not match:
        raise HTTPException(status_code=404, detail="This user does not have access to the resource")
    match["permission"] = data.permission
    return match


@router.post("/{resource_id}/owner", response_model=ResourceAccessOut)
def transfer_resource_owner(
    resource_id: str,
    data: ResourceOwnerRequest,
    current_user: dict = Depends(get_current_user),
):
    if resource_owners_db.get(resource_id) != current_user["email"]:
        raise HTTPException(status_code=403, detail="Only the resource owner can perform this action")

    resource_owners_db[resource_id] = data.new_owner_email
    return ResourceAccessOut(
        resource_id=resource_id,
        owner_email=resource_owners_db[resource_id],
        locked=resource_locks_db.get(resource_id, False),
        shared_with_count=len(resource_shares_db.get(resource_id, [])),
    )


@router.get("/{resource_id}/access", response_model=ResourceAccessOut)
def get_resource_access(
    resource_id: str,
    current_user: dict = Depends(get_current_user),
):
    return ResourceAccessOut(
        resource_id=resource_id,
        owner_email=resource_owners_db.get(resource_id),
        locked=resource_locks_db.get(resource_id, False),
        shared_with_count=len(resource_shares_db.get(resource_id, [])),
    )


@router.post("/{resource_id}/lock", response_model=ResourceLockResponse)
def lock_resource(
    resource_id: str,
    current_user: dict = Depends(get_current_user),
):
    _require_owner_or_claim(resource_id, current_user)
    resource_locks_db[resource_id] = True
    return ResourceLockResponse(resource_id=resource_id, locked=True)


@router.post("/{resource_id}/unlock", response_model=ResourceLockResponse)
def unlock_resource(
    resource_id: str,
    current_user: dict = Depends(get_current_user),
):
    if resource_owners_db.get(resource_id) != current_user["email"]:
        raise HTTPException(status_code=403, detail="Only the resource owner can perform this action")
    resource_locks_db[resource_id] = False
    return ResourceLockResponse(resource_id=resource_id, locked=False)


@router.post("/{resource_id}/inherit", response_model=ResourcePermissionsOut)
def inherit_resource_permissions(
    resource_id: str,
    data: ResourceInheritRequest,
    current_user: dict = Depends(get_current_user),
):
    _require_owner_or_claim(resource_id, current_user)
    _require_unlocked(resource_id)

    parent_shares = resource_shares_db.get(data.parent_resource_id, [])
    inherited = [
        {"id": str(uuid4()), "resource_id": resource_id, "email": s["email"], "permission": s["permission"]}
        for s in parent_shares
    ]
    resource_shares_db.setdefault(resource_id, []).extend(inherited)

    return ResourcePermissionsOut(
        resource_id=resource_id,
        owner_email=resource_owners_db.get(resource_id),
        shares=resource_shares_db.get(resource_id, []),
    )


@router.post("/{resource_id}/revoke-all", response_model=ResourceRevokeAllResponse)
def revoke_all_resource_access(
    resource_id: str,
    current_user: dict = Depends(get_current_user),
):
    if resource_owners_db.get(resource_id) != current_user["email"]:
        raise HTTPException(status_code=403, detail="Only the resource owner can perform this action")

    count = len(resource_shares_db.get(resource_id, []))
    resource_shares_db[resource_id] = []
    return ResourceRevokeAllResponse(resource_id=resource_id, revoked_count=count)
