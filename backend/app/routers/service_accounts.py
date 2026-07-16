"""
Service Accounts router — create, list, update, delete, roles, permissions, access, rotate-secret.
Matches the Auth blueprint's Service Accounts section (4/4) plus the
Authorization blueprint's Service Accounts section additions (6 more, 10/10 combined).
"""

import secrets as secrets_module
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.service_accounts import (
    ServiceAccountCreateRequest,
    ServiceAccountUpdateRequest,
    ServiceAccountOut,
    ServiceAccountRoleAddRequest,
    ServiceAccountPermissionAddRequest,
    ServiceAccountAccessOut,
    ServiceAccountRotateSecretResponse,
)
from app.models.user import (
    service_accounts_db,
    service_account_roles_db,
    service_account_permissions_db,
    service_account_secrets_db,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/service-accounts", tags=["Service Accounts"])


def _get_owned_account(account_id: str, current_user: dict) -> dict:
    account = service_accounts_db.get(account_id)
    if not account or account["owner_email"] != current_user["email"]:
        raise HTTPException(status_code=404, detail="Service account not found")
    return account


@router.post("", response_model=ServiceAccountOut, status_code=201)
def create_service_account(
    data: ServiceAccountCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    account_id = str(uuid4())
    account = {
        "id": account_id,
        "name": data.name,
        "owner_email": current_user["email"],
        "active": True,
        "created_at": datetime.now(timezone.utc),
    }
    service_accounts_db[account_id] = account
    service_account_roles_db[account_id] = []
    service_account_permissions_db[account_id] = []
    return account


@router.get("", response_model=list[ServiceAccountOut])
def list_service_accounts(current_user: dict = Depends(get_current_user)):
    email = current_user["email"]
    return [acc for acc in service_accounts_db.values() if acc["owner_email"] == email]


@router.patch("/{account_id}", response_model=ServiceAccountOut)
def update_service_account(
    account_id: str,
    data: ServiceAccountUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    account = _get_owned_account(account_id, current_user)
    if data.name is not None:
        account["name"] = data.name
    if data.active is not None:
        account["active"] = data.active
    return account


@router.delete("/{account_id}", status_code=204)
def delete_service_account(
    account_id: str,
    current_user: dict = Depends(get_current_user),
):
    _get_owned_account(account_id, current_user)
    del service_accounts_db[account_id]
    service_account_roles_db.pop(account_id, None)
    service_account_permissions_db.pop(account_id, None)
    service_account_secrets_db.pop(account_id, None)
    return None


@router.post("/{account_id}/roles", response_model=ServiceAccountAccessOut, status_code=201)
def add_service_account_role(
    account_id: str,
    data: ServiceAccountRoleAddRequest,
    current_user: dict = Depends(get_current_user),
):
    account = _get_owned_account(account_id, current_user)
    roles = service_account_roles_db.setdefault(account_id, [])
    if data.role not in roles:
        roles.append(data.role)
    return ServiceAccountAccessOut(
        id=account_id,
        active=account["active"],
        roles=roles,
        permissions=service_account_permissions_db.get(account_id, []),
    )


@router.delete("/{account_id}/roles/{role_id}", response_model=ServiceAccountAccessOut)
def remove_service_account_role(
    account_id: str,
    role_id: str,
    current_user: dict = Depends(get_current_user),
):
    account = _get_owned_account(account_id, current_user)
    roles = service_account_roles_db.get(account_id, [])
    if role_id not in roles:
        raise HTTPException(status_code=404, detail="Role not assigned to this service account")
    roles.remove(role_id)
    return ServiceAccountAccessOut(
        id=account_id,
        active=account["active"],
        roles=roles,
        permissions=service_account_permissions_db.get(account_id, []),
    )


@router.post("/{account_id}/permissions", response_model=ServiceAccountAccessOut, status_code=201)
def add_service_account_permission(
    account_id: str,
    data: ServiceAccountPermissionAddRequest,
    current_user: dict = Depends(get_current_user),
):
    account = _get_owned_account(account_id, current_user)
    perms = service_account_permissions_db.setdefault(account_id, [])
    if data.permission not in perms:
        perms.append(data.permission)
    return ServiceAccountAccessOut(
        id=account_id,
        active=account["active"],
        roles=service_account_roles_db.get(account_id, []),
        permissions=perms,
    )


@router.delete("/{account_id}/permissions/{permission_id}", response_model=ServiceAccountAccessOut)
def remove_service_account_permission(
    account_id: str,
    permission_id: str,
    current_user: dict = Depends(get_current_user),
):
    account = _get_owned_account(account_id, current_user)
    perms = service_account_permissions_db.get(account_id, [])
    if permission_id not in perms:
        raise HTTPException(status_code=404, detail="Permission not assigned to this service account")
    perms.remove(permission_id)
    return ServiceAccountAccessOut(
        id=account_id,
        active=account["active"],
        roles=service_account_roles_db.get(account_id, []),
        permissions=perms,
    )


@router.get("/{account_id}/access", response_model=ServiceAccountAccessOut)
def get_service_account_access(
    account_id: str,
    current_user: dict = Depends(get_current_user),
):
    account = _get_owned_account(account_id, current_user)
    return ServiceAccountAccessOut(
        id=account_id,
        active=account["active"],
        roles=service_account_roles_db.get(account_id, []),
        permissions=service_account_permissions_db.get(account_id, []),
    )


@router.post("/{account_id}/rotate-secret", response_model=ServiceAccountRotateSecretResponse)
def rotate_service_account_secret(
    account_id: str,
    current_user: dict = Depends(get_current_user),
):
    _get_owned_account(account_id, current_user)
    new_secret = secrets_module.token_urlsafe(32)
    service_account_secrets_db[account_id] = new_secret
    return ServiceAccountRotateSecretResponse(
        id=account_id,
        secret=new_secret,
        message="Secret rotated successfully. Store it now — it will not be shown again.",
    )