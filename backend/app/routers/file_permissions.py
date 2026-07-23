"""
File Permissions router — grant/revoke access, share links, invites, audit.
Matches the Permissions section of the File & Storage APIs blueprint (8/8).

Mounted at /api/v1/files/permissions (NOT /api/v1/permissions, which is
already used by the Authorization domain's roles/permission-key router).

Only the file owner can grant, update, revoke, or invite access to their file.
"""

import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.file_permissions import (
    FilePermissionCreateRequest,
    FilePermissionUpdateRequest,
    FilePermissionResponse,
    ShareLinkCreateRequest,
    ShareLinkResponse,
    ShareLinkRevokeRequest,
    FileInviteRequest,
    FileInviteResponse,
    PermissionAuditEntry,
)
from app.core.security import get_current_user
from app.routers.fileslifecycle import files_db, _get_file_or_404, _require_owner

router = APIRouter(prefix="/api/v1/files/permissions", tags=["File Permissions"])

VALID_ACCESS_LEVELS = {"viewer", "editor", "owner"}

# id -> {id, file_id, grantee_email, access_level, granted_by_email, created_at, updated_at}
file_permissions_db: dict[str, dict] = {}

# link_token -> {file_id, access_level, expires_at}
share_links_db: dict[str, dict] = {}

# append-only audit log
permission_audit_db: list[dict] = []


def _validate_access_level(level: str):
    if level not in VALID_ACCESS_LEVELS:
        raise HTTPException(
            status_code=422,
            detail=f"access_level must be one of {sorted(VALID_ACCESS_LEVELS)}",
        )


def _log_audit(file_id: str, action: str, actor_email: str, target_email: str | None = None):
    permission_audit_db.append(
        {
            "file_id": file_id,
            "action": action,
            "actor_email": actor_email,
            "target_email": target_email,
            "timestamp": datetime.now(timezone.utc),
        }
    )


@router.get("", response_model=list[FilePermissionResponse])
def list_permissions(current_user: dict = Depends(get_current_user)):
    """List all permission grants for files the current user owns."""
    owned_file_ids = {
        f["id"] for f in files_db.values() if f["owner_email"] == current_user["email"]
    }
    return [
        p for p in file_permissions_db.values() if p["file_id"] in owned_file_ids
    ]


@router.post("", response_model=FilePermissionResponse, status_code=201)
def grant_permission(
    data: FilePermissionCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    file = _get_file_or_404(data.file_id)
    _require_owner(file, current_user["email"])
    _validate_access_level(data.access_level)

    perm_id = str(uuid4())
    now = datetime.now(timezone.utc)
    file_permissions_db[perm_id] = {
        "id": perm_id,
        "file_id": data.file_id,
        "grantee_email": data.grantee_email,
        "access_level": data.access_level,
        "granted_by_email": current_user["email"],
        "created_at": now,
        "updated_at": now,
    }
    _log_audit(data.file_id, "grant", current_user["email"], data.grantee_email)
    return file_permissions_db[perm_id]


# ─── Literal-path routes MUST come before any /{id} routes below ───

@router.post("/share-link", response_model=ShareLinkResponse, status_code=201)
def create_share_link(
    data: ShareLinkCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    file = _get_file_or_404(data.file_id)
    _require_owner(file, current_user["email"])
    _validate_access_level(data.access_level or "viewer")

    token = secrets.token_urlsafe(16)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=data.expires_in_seconds or 86400)
    share_links_db[token] = {
        "file_id": data.file_id,
        "access_level": data.access_level or "viewer",
        "expires_at": expires_at,
    }
    _log_audit(data.file_id, "share_link_created", current_user["email"])
    return ShareLinkResponse(
        file_id=data.file_id,
        link_token=token,
        url=f"https://dios.example.com/share/{token}",
        access_level=data.access_level or "viewer",
        expires_at=expires_at,
    )


@router.delete("/share-link", status_code=204)
def revoke_share_link(
    data: ShareLinkRevokeRequest,
    current_user: dict = Depends(get_current_user),
):
    file = _get_file_or_404(data.file_id)
    _require_owner(file, current_user["email"])

    link = share_links_db.get(data.link_token)
    if not link or link["file_id"] != data.file_id:
        raise HTTPException(status_code=404, detail="Share link not found for this file")

    del share_links_db[data.link_token]
    _log_audit(data.file_id, "share_link_revoked", current_user["email"])
    return None


@router.post("/invite", response_model=FileInviteResponse, status_code=201)
def invite_to_file(
    data: FileInviteRequest,
    current_user: dict = Depends(get_current_user),
):
    file = _get_file_or_404(data.file_id)
    _require_owner(file, current_user["email"])
    _validate_access_level(data.access_level or "viewer")

    # Mock invite: directly grants access (no real email sending in this environment)
    perm_id = str(uuid4())
    now = datetime.now(timezone.utc)
    file_permissions_db[perm_id] = {
        "id": perm_id,
        "file_id": data.file_id,
        "grantee_email": data.email,
        "access_level": data.access_level or "viewer",
        "granted_by_email": current_user["email"],
        "created_at": now,
        "updated_at": now,
    }
    _log_audit(data.file_id, "invited", current_user["email"], data.email)
    return FileInviteResponse(
        file_id=data.file_id,
        invited_email=data.email,
        access_level=data.access_level or "viewer",
        invited_by_email=current_user["email"],
        invited_at=now,
    )


@router.get("/audit", response_model=list[PermissionAuditEntry])
def get_permission_audit(current_user: dict = Depends(get_current_user)):
    """Audit log for files the current user owns."""
    owned_file_ids = {
        f["id"] for f in files_db.values() if f["owner_email"] == current_user["email"]
    }
    return [entry for entry in permission_audit_db if entry["file_id"] in owned_file_ids]


# ─── Dynamic /{id} routes come LAST ───

@router.patch("/{id}", response_model=FilePermissionResponse)
def update_permission(
    id: str,
    data: FilePermissionUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    perm = file_permissions_db.get(id)
    if not perm:
        raise HTTPException(status_code=404, detail="Permission not found")
    file = _get_file_or_404(perm["file_id"])
    _require_owner(file, current_user["email"])
    _validate_access_level(data.access_level)

    perm["access_level"] = data.access_level
    perm["updated_at"] = datetime.now(timezone.utc)
    _log_audit(perm["file_id"], "updated", current_user["email"], perm["grantee_email"])
    return perm


@router.delete("/{id}", status_code=204)
def revoke_permission(id: str, current_user: dict = Depends(get_current_user)):
    perm = file_permissions_db.get(id)
    if not perm:
        raise HTTPException(status_code=404, detail="Permission not found")
    file = _get_file_or_404(perm["file_id"])
    _require_owner(file, current_user["email"])

    _log_audit(perm["file_id"], "revoked", current_user["email"], perm["grantee_email"])
    del file_permissions_db[id]
    return None