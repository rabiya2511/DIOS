"""
Admin router — Organization & Roles.
Matches section 2 of the Administration blueprint (6/6).
All endpoints require admin privileges.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.admin_org_roles import (
    AdminOrganizationOut,
    AdminOrganizationUpdateRequest,
    AdminRoleOut,
    AdminRoleCreateRequest,
    AdminPermissionUpdateRequest,
    AdminPermissionOut,
    AdminPoliciesOut,
)
from app.models.user import organizations_db, roles_db, permission_overrides_db, policies_db
from app.core.security import get_current_admin
from app.routers.permissions import permissions_db

router = APIRouter(prefix="/api/v1/admin", tags=["Admin: Organization & Roles"])


@router.get("/organizations", response_model=list[AdminOrganizationOut])
def list_organizations(current_admin: dict = Depends(get_current_admin)):
    return list(organizations_db.values())


@router.patch("/organizations/{org_id}", response_model=AdminOrganizationOut)
def update_organization(
    org_id: str,
    data: AdminOrganizationUpdateRequest,
    current_admin: dict = Depends(get_current_admin),
):
    org = organizations_db.get(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    if data.name is not None:
        org["name"] = data.name
    if data.owner_email is not None:
        org["owner_email"] = data.owner_email

    return org


@router.get("/roles", response_model=list[AdminRoleOut])
def list_roles_admin(current_admin: dict = Depends(get_current_admin)):
    return list(roles_db.values())


@router.post("/roles", response_model=AdminRoleOut, status_code=201)
def create_role_admin(
    data: AdminRoleCreateRequest,
    current_admin: dict = Depends(get_current_admin),
):
    role_id = str(uuid4())
    role = {
        "id": role_id,
        "name": data.name,
        "permissions": data.permissions,
        "created_at": datetime.now(timezone.utc),
    }
    roles_db[role_id] = role
    return role


@router.patch("/permissions", response_model=AdminPermissionOut)
def update_permission_description(
    data: AdminPermissionUpdateRequest,
    current_admin: dict = Depends(get_current_admin),
):
    valid_keys = {p["key"] for p in permissions_db.values()}
    if data.key not in valid_keys:
        raise HTTPException(status_code=404, detail="Permission key not found")

    permission_overrides_db[data.key] = data.description
    return AdminPermissionOut(key=data.key, description=data.description)


@router.get("/policies", response_model=AdminPoliciesOut)
def get_policies(current_admin: dict = Depends(get_current_admin)):
    return policies_db