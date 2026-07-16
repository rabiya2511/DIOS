"""
Teams router — CRUD, members, permissions.
Matches the Team Authorization section of the Authorization APIs
blueprint (10/10). Only the team creator can update/delete the team
or manage its members/permissions.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.teams import (
    TeamCreateRequest,
    TeamUpdateRequest,
    TeamResponse,
    TeamMemberAddRequest,
    TeamMemberResponse,
    TeamPermissionGrantRequest,
    TeamPermissionResponse,
)
from app.routers.permissions import permissions_db
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/teams", tags=["Team Authorization"])

# id -> {id, name, description, creator_email, created_at}
teams_db: dict[str, dict] = {}

# team_id -> set of member emails
team_members_db: dict[str, set] = {}

# team_id -> {permission_key: {"granted_at": datetime}}
team_permissions_db: dict[str, dict[str, dict]] = {}


def _get_team_or_404(id: str) -> dict:
    team = teams_db.get(id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


def _require_creator(team: dict, email: str):
    if team["creator_email"] != email:
        raise HTTPException(status_code=403, detail="Only the team creator can perform this action")


@router.get("", response_model=list[TeamResponse])
def list_teams(current_user: dict = Depends(get_current_user)):
    return [
        team
        for team in teams_db.values()
        if current_user["email"] in team_members_db.get(team["id"], set())
    ]


@router.post("", response_model=TeamResponse, status_code=201)
def create_team(
    data: TeamCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    team_id = str(uuid4())
    now = datetime.now(timezone.utc)
    teams_db[team_id] = {
        "id": team_id,
        "name": data.name,
        "description": data.description,
        "creator_email": current_user["email"],
        "created_at": now,
    }
    team_members_db[team_id] = {current_user["email"]}
    team_permissions_db[team_id] = {}
    return teams_db[team_id]


@router.patch("/{id}", response_model=TeamResponse)
def update_team(
    id: str,
    data: TeamUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    team = _get_team_or_404(id)
    _require_creator(team, current_user["email"])
    if data.name is not None:
        team["name"] = data.name
    if data.description is not None:
        team["description"] = data.description
    return team


@router.delete("/{id}", status_code=204)
def delete_team(id: str, current_user: dict = Depends(get_current_user)):
    team = _get_team_or_404(id)
    _require_creator(team, current_user["email"])
    del teams_db[id]
    team_members_db.pop(id, None)
    team_permissions_db.pop(id, None)
    return None


@router.get("/{id}/members", response_model=list[TeamMemberResponse])
def get_team_members(id: str, current_user: dict = Depends(get_current_user)):
    team = _get_team_or_404(id)
    members = team_members_db.get(id, set())
    if current_user["email"] not in members:
        raise HTTPException(status_code=403, detail="Not a member of this team")
    return [TeamMemberResponse(email=e) for e in sorted(members)]


@router.post("/{id}/members", response_model=TeamMemberResponse, status_code=201)
def add_team_member(
    id: str,
    data: TeamMemberAddRequest,
    current_user: dict = Depends(get_current_user),
):
    team = _get_team_or_404(id)
    _require_creator(team, current_user["email"])
    team_members_db.setdefault(id, set()).add(data.email)
    return TeamMemberResponse(email=data.email)


@router.delete("/{id}/members/{userId}", status_code=204)
def remove_team_member(
    id: str,
    userId: str,
    current_user: dict = Depends(get_current_user),
):
    team = _get_team_or_404(id)
    _require_creator(team, current_user["email"])
    if userId == team["creator_email"]:
        raise HTTPException(status_code=400, detail="Cannot remove the team creator")

    members = team_members_db.get(id, set())
    if userId not in members:
        raise HTTPException(status_code=404, detail="Member not found in team")
    members.discard(userId)
    return None


@router.get("/{id}/permissions", response_model=list[TeamPermissionResponse])
def get_team_permissions(id: str, current_user: dict = Depends(get_current_user)):
    _get_team_or_404(id)
    grants = team_permissions_db.get(id, {})
    return [TeamPermissionResponse(key=k, granted_at=v["granted_at"]) for k, v in grants.items()]


@router.post("/{id}/permissions", response_model=TeamPermissionResponse, status_code=201)
def grant_team_permission(
    id: str,
    data: TeamPermissionGrantRequest,
    current_user: dict = Depends(get_current_user),
):
    team = _get_team_or_404(id)
    _require_creator(team, current_user["email"])

    if not any(p["key"] == data.key for p in permissions_db.values()):
        raise HTTPException(status_code=404, detail=f"Permission key '{data.key}' does not exist")

    now = datetime.now(timezone.utc)
    team_permissions_db.setdefault(id, {})[data.key] = {"granted_at": now}
    return TeamPermissionResponse(key=data.key, granted_at=now)


@router.delete("/{id}/permissions/{permissionId}", status_code=204)
def revoke_team_permission(
    id: str,
    permissionId: str,
    current_user: dict = Depends(get_current_user),
):
    team = _get_team_or_404(id)
    _require_creator(team, current_user["email"])

    grants = team_permissions_db.get(id, {})
    if permissionId not in grants:
        raise HTTPException(status_code=404, detail="This permission is not granted to this team")
    del grants[permissionId]
    return None