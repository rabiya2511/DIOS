"""
Permissions router — CRUD, import, export, catalog, validate, history.
Matches the Permissions section of the Authorization APIs blueprint (10/10).
Seeded with the same 8 keys that used to live as a static list in roles.py.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.permissions import (
    PermissionCreateRequest,
    PermissionUpdateRequest,
    PermissionResponse,
    PermissionImportRequest,
    PermissionImportResponse,
    PermissionExportResponse,
    PermissionCatalogGroup,
    PermissionValidateRequest,
    PermissionValidateResponse,
    PermissionHistoryEntry,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/permissions", tags=["Permissions"])

# id -> {id, key, resource, action, description, created_at, updated_at}
permissions_db: dict[str, dict] = {}

# append-only audit log
permission_history_db: list[dict] = []

SEED_PERMISSIONS = [
    ("users:read", "View user profiles"),
    ("users:write", "Create or edit users"),
    ("users:delete", "Delete users"),
    ("organizations:read", "View organizations"),
    ("organizations:write", "Create or edit organizations"),
    ("roles:manage", "Create, edit, or delete roles"),
    ("api_keys:manage", "Create, rotate, or revoke API keys"),
    ("audit:read", "View audit logs and security events"),
]


def _split_key(key: str) -> tuple[str, str]:
    if ":" not in key:
        raise HTTPException(status_code=422, detail="Permission key must be formatted 'resource:action'")
    resource, action = key.split(":", 1)
    return resource, action


def _log_history(permission_id: str, key: str, action: str):
    permission_history_db.append(
        {
            "permission_id": permission_id,
            "key": key,
            "action": action,
            "timestamp": datetime.now(timezone.utc),
        }
    )


def _seed_permissions():
    if permissions_db:
        return
    for key, description in SEED_PERMISSIONS:
        resource, action = _split_key(key)
        pid = str(uuid4())
        now = datetime.now(timezone.utc)
        permissions_db[pid] = {
            "id": pid,
            "key": key,
            "resource": resource,
            "action": action,
            "description": description,
            "created_at": now,
            "updated_at": now,
        }
        _log_history(pid, key, "created")


_seed_permissions()


def _get_permission_or_404(id: str) -> dict:
    perm = permissions_db.get(id)
    if not perm:
        raise HTTPException(status_code=404, detail="Permission not found")
    return perm


def _key_exists(key: str) -> bool:
    return any(p["key"] == key for p in permissions_db.values())


@router.get("", response_model=list[PermissionResponse])
def list_permissions():
    return list(permissions_db.values())


@router.get("/catalog", response_model=list[PermissionCatalogGroup])
def get_catalog():
    groups: dict[str, list[dict]] = {}
    for perm in permissions_db.values():
        groups.setdefault(perm["resource"], []).append(perm)
    return [
        PermissionCatalogGroup(resource=resource, permissions=perms)
        for resource, perms in sorted(groups.items())
    ]


@router.get("/history", response_model=list[PermissionHistoryEntry])
def get_history():
    return list(permission_history_db)


@router.get("/{id}", response_model=PermissionResponse)
def get_permission(id: str):
    return _get_permission_or_404(id)


@router.post("", response_model=PermissionResponse, status_code=201)
def create_permission(
    data: PermissionCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    if _key_exists(data.key):
        raise HTTPException(status_code=409, detail=f"Permission key '{data.key}' already exists")
    resource, action = _split_key(data.key)
    pid = str(uuid4())
    now = datetime.now(timezone.utc)
    permissions_db[pid] = {
        "id": pid,
        "key": data.key,
        "resource": resource,
        "action": action,
        "description": data.description,
        "created_at": now,
        "updated_at": now,
    }
    _log_history(pid, data.key, "created")
    return permissions_db[pid]


@router.patch("/{id}", response_model=PermissionResponse)
def update_permission(
    id: str,
    data: PermissionUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    perm = _get_permission_or_404(id)
    if data.description is not None:
        perm["description"] = data.description
    perm["updated_at"] = datetime.now(timezone.utc)
    _log_history(id, perm["key"], "updated")
    return perm


@router.delete("/{id}", status_code=204)
def delete_permission(id: str, current_user: dict = Depends(get_current_user)):
    perm = _get_permission_or_404(id)
    _log_history(id, perm["key"], "deleted")
    del permissions_db[id]
    return None


@router.post("/import", response_model=PermissionImportResponse)
def import_permissions(
    data: PermissionImportRequest,
    current_user: dict = Depends(get_current_user),
):
    imported = 0
    skipped = 0
    for item in data.permissions:
        if _key_exists(item.key):
            skipped += 1
            continue
        resource, action = _split_key(item.key)
        pid = str(uuid4())
        now = datetime.now(timezone.utc)
        permissions_db[pid] = {
            "id": pid,
            "key": item.key,
            "resource": resource,
            "action": action,
            "description": item.description,
            "created_at": now,
            "updated_at": now,
        }
        _log_history(pid, item.key, "created")
        imported += 1
    return PermissionImportResponse(imported=imported, skipped=skipped)


@router.post("/export", response_model=PermissionExportResponse)
def export_permissions(current_user: dict = Depends(get_current_user)):
    return PermissionExportResponse(permissions=list(permissions_db.values()))


@router.post("/validate", response_model=PermissionValidateResponse)
def validate_permission(data: PermissionValidateRequest):
    return PermissionValidateResponse(valid=_key_exists(data.key), key=data.key)