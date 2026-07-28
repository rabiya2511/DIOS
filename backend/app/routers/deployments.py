"""
Deployment Management router — CRUD, rollback, history.
Matches the Deployment Management section of the Deployment &
Infrastructure APIs blueprint (6/6).
Only the deployment owner can update/delete/rollback their own deployment.

Storage lives in app/models/user.py (deployments_db, deployment_history_db,
deployment_versions_db) and is imported here, matching this codebase's
convention (see workspaces.py, activity.py, etc.) rather than declaring
local dicts in the router file.

ASSUMPTIONS:
- Every deployment tracks a simple, in-memory version timeline
  (deployment_versions_db: deployment_id -> [versions in chronological
  order, including rollbacks]). POST /deployments/rollback with no
  target_version rolls back to the version immediately before the current
  one in that timeline. If you pass an explicit target_version, it's
  applied directly without validating it against real deployment
  infrastructure (there isn't any here — this is all in-memory bookkeeping,
  not a real deploy/rollback mechanism).
- GET /deployments/history returns history entries for the caller's own
  deployments only, optionally filtered by ?deployment_id=.
- Literal-path routes (/rollback, /history) MUST come before the dynamic
  /{id} routes below — same ordering rule used throughout this codebase.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query

from app.schemas.deployments import (
    DeploymentCreateRequest,
    DeploymentUpdateRequest,
    DeploymentOut,
    DeploymentRollbackRequest,
    DeploymentHistoryEntry,
)
from app.models.user import deployments_db, deployment_history_db, deployment_versions_db
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/deployments", tags=["Deployment Management"])


def _get_deployment_or_404(id: str) -> dict:
    deployment = deployments_db.get(id)
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    return deployment


def _require_owner(deployment: dict, email: str):
    if deployment["owner_email"] != email:
        raise HTTPException(status_code=403, detail="Only the deployment owner can perform this action")


def _record_history(deployment_id: str, action: str, version: str, now: datetime):
    entry = {
        "id": str(uuid4()),
        "deployment_id": deployment_id,
        "action": action,
        "version": version,
        "timestamp": now,
    }
    deployment_history_db.setdefault(deployment_id, []).append(entry)
    deployment_versions_db.setdefault(deployment_id, []).append(version)


@router.get("", response_model=list[DeploymentOut])
def list_deployments(current_user: dict = Depends(get_current_user)):
    return [
        d for d in deployments_db.values()
        if d["owner_email"] == current_user["email"]
    ]


@router.post("", response_model=DeploymentOut, status_code=201)
def create_deployment(
    data: DeploymentCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    deployment_id = str(uuid4())
    now = datetime.now(timezone.utc)
    deployments_db[deployment_id] = {
        "id": deployment_id,
        "name": data.name,
        "version": data.version,
        "environment": data.environment,
        "status": "active",
        "owner_email": current_user["email"],
        "created_at": now,
        "updated_at": now,
    }
    _record_history(deployment_id, "created", data.version, now)
    return deployments_db[deployment_id]


# ─── Literal-path routes MUST come before any /{id} routes below ───

@router.post("/rollback", response_model=DeploymentOut)
def rollback_deployment(
    data: DeploymentRollbackRequest,
    current_user: dict = Depends(get_current_user),
):
    deployment = _get_deployment_or_404(data.deployment_id)
    _require_owner(deployment, current_user["email"])

    versions = deployment_versions_db.get(data.deployment_id, [])
    if data.target_version is not None:
        target = data.target_version
    else:
        if len(versions) < 2:
            raise HTTPException(
                status_code=400,
                detail="No earlier version to roll back to for this deployment",
            )
        target = versions[-2]

    now = datetime.now(timezone.utc)
    deployment["version"] = target
    deployment["status"] = "rolled_back"
    deployment["updated_at"] = now
    _record_history(data.deployment_id, "rolled_back", target, now)
    return deployment


@router.get("/history", response_model=list[DeploymentHistoryEntry])
def get_deployment_history(
    deployment_id: str | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
):
    owned_ids = {
        d["id"] for d in deployments_db.values()
        if d["owner_email"] == current_user["email"]
    }
    entries: list[dict] = []
    for did, history in deployment_history_db.items():
        if did not in owned_ids:
            continue
        if deployment_id is not None and did != deployment_id:
            continue
        entries.extend(history)
    entries.sort(key=lambda e: e["timestamp"], reverse=True)
    return entries


# ─── Dynamic /{id} routes come LAST ───

@router.patch("/{id}", response_model=DeploymentOut)
def update_deployment(
    id: str,
    data: DeploymentUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    deployment = _get_deployment_or_404(id)
    _require_owner(deployment, current_user["email"])
    now = datetime.now(timezone.utc)

    if data.name is not None:
        deployment["name"] = data.name
    if data.environment is not None:
        deployment["environment"] = data.environment
    if data.version is not None and data.version != deployment["version"]:
        deployment["version"] = data.version
        deployment["status"] = "active"
        _record_history(id, "updated", data.version, now)

    deployment["updated_at"] = now
    return deployment


@router.delete("/{id}", status_code=204)
def delete_deployment(id: str, current_user: dict = Depends(get_current_user)):
    deployment = _get_deployment_or_404(id)
    _require_owner(deployment, current_user["email"])
    del deployments_db[id]
    deployment_history_db.pop(id, None)
    deployment_versions_db.pop(id, None)
    return None