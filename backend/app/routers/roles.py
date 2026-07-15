"""
Roles & Permissions router — roles CRUD + fixed permissions list,
plus clone/archive/restore and system/custom views (Authorization blueprint).
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


def _seed_system_roles():
    if any(r.get("is_system") for r in roles_db.values()):
        return
    now = datetime.now(timezone.utc)
    for name, perms in [
        ("Admin", ["*"]),
        ("Editor", ["users:read", "users:write", "organizations:read", "organizations:write"]),
        ("Viewer", ["users:read", "organizations:read"]),
    ]:
        role_id = str(uuid4())
        roles_db[role_id] = {
            "id": role_id,
            "name": name,
            "permissions": perms,
            "created_at": now,
            "description": f"Built-in {name} role",
            "is_system": True,
            "archived": False,
        }


_seed_system_roles()


def _get_role_or_404(role_id: str) -> dict:
    role = roles_db.get(role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return role


def _require_custom(role: dict, action: str):
    if role.get("is_system"):
        raise HTTPException(status_code=403, detail=f"System roles cannot be {action}")


@router.get("/permissions", response_model=list[PermissionOut])
def list_permissions(current_user: dict = Depends(get_current_user)):
    return AVAILABLE_PERMISSIONS


@router.get("/roles", response_model=list[RoleOut])
def list_roles(current_user: dict = Depends(get_current_user)):
    return list(roles_db.values())


@router.get("/roles/system", response_model=list[RoleOut])
def list_system_roles(current_user: dict = Depends(get_current_user)):
    return [r for r in roles_db.values() if r.get("is_system")]


@router.get("/roles/custom", response_model=list[RoleOut])
def list_custom_roles(current_user: dict = Depends(get_current_user)):
    return [r for r in roles_db.values() if not r.get("is_system")]


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
        "description": None,
        "is_system": False,
        "archived": False,
    }
    roles_db[role_id] = role
    return role


@router.get("/roles/{role_id}", response_model=RoleOut)
def get_role(
    role_id: str,
    current_user: dict = Depends(get_current_user),
):
    return _get_role_or_404(role_id)


@router.patch("/roles/{role_id}", response_model=RoleOut)
def update_role(
    role_id: str,
    data: RoleUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    role = _get_role_or_404(role_id)
    _require_custom(role, "edited")
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
    role = _get_role_or_404(role_id)
    _require_custom(role, "deleted")
    del roles_db[role_id]
    return None


@router.post("/roles/{role_id}/clone", response_model=RoleOut, status_code=201)
def clone_role(
    role_id: str,
    current_user: dict = Depends(get_current_user),
):
    source = _get_role_or_404(role_id)
    new_id = str(uuid4())
    role = {
        "id": new_id,
        "name": f"{source['name']} (Copy)",
        "permissions": list(source["permissions"]),
        "created_at": datetime.now(timezone.utc),
        "description": source.get("description"),
        "is_system": False,
        "archived": False,
    }
    roles_db[new_id] = role
    return role


@router.post("/roles/{role_id}/archive", response_model=RoleOut)
def archive_role(
    role_id: str,
    current_user: dict = Depends(get_current_user),
):
    role = _get_role_or_404(role_id)
    _require_custom(role, "archived")
    role["archived"] = True
    return role


@router.post("/roles/{role_id}/restore", response_model=RoleOut)
def restore_role(
    role_id: str,
    current_user: dict = Depends(get_current_user),
):
    role = _get_role_or_404(role_id)
    _require_custom(role, "restored")
    role["archived"] = False
    return role