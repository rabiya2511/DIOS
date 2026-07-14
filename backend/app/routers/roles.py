"""
Roles & Permissions router — roles CRUD + fixed permissions list.
Matches the Roles & Permissions section of the Auth blueprint (5/5).
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.roles import (
    RoleCreateRequest,
    RoleUpdateRequest,
    RoleOut,
    PermissionOut,
)
from app.models.user import roles_db
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1", tags=["Roles & Permissions"])

# Fixed reference list — not user-editable, just describes what's available to assign.
AVAILABLE_PERMISSIONS = [
    {"key": "users:read", "description": "View user profiles"},
    {"key": "users:write", "description": "Create or edit users"},
    {"key": "users:delete", "description": "Delete users"},
    {"key": "organizations:read", "description": "View organizations"},
    {"key": "organizations:write", "description": "Create or edit organizations"},
    {"key": "roles:manage", "description": "Create, edit, or delete roles"},
    {"key": "api_keys:manage", "description": "Create, rotate, or revoke API keys"},
    {"key": "audit:read", "description": "View audit logs and security events"},
]


@router.get("/permissions", response_model=list[PermissionOut])
def list_permissions(current_user: dict = Depends(get_current_user)):
    return AVAILABLE_PERMISSIONS


@router.get("/roles", response_model=list[RoleOut])
def list_roles(current_user: dict = Depends(get_current_user)):
    return list(roles_db.values())


@router.post("/roles", response_model=RoleOut, status_code=201)
def create_role(
    data: RoleCreateRequest,
    current_user: dict = Depends(get_current_user),
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


@router.patch("/roles/{role_id}", response_model=RoleOut)
def update_role(
    role_id: str,
    data: RoleUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    role = roles_db.get(role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    if data.name is not None:
        role["name"] = data.name
    if data.permissions is not None:
        role["permissions"] = data.permissions

    return role


@router.delete("/roles/{role_id}", status_code=204)
def delete_role(
    role_id: str,
    current_user: dict = Depends(get_current_user),
):
    if role_id not in roles_db:
        raise HTTPException(status_code=404, detail="Role not found")

    del roles_db[role_id]
    return None