"""
Groups router — full CRUD + membership management.
Matches the Groups section of the User Management blueprint (8/8).
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.groups import (
    GroupCreateRequest,
    GroupUpdateRequest,
    GroupResponse,
    GroupMemberRequest,
    GroupMembersResponse,
    GroupSearchRequest,
)
from app.models.group import groups_db, group_members_db
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/groups", tags=["Groups"])


@router.get("", response_model=list[GroupResponse])
def list_groups(current_user: dict = Depends(get_current_user)):
    return list(groups_db.values())


@router.post("", response_model=GroupResponse, status_code=201)
def create_group(
    data: GroupCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    group_id = str(uuid4())
    group = {
        "id": group_id,
        "name": data.name,
        "description": data.description,
        "created_at": datetime.now(timezone.utc),
    }
    groups_db[group_id] = group
    group_members_db[group_id] = []
    return group


# ─── Fixed literal-path routes MUST come before /{group_id} routes ───

@router.post("/member", status_code=201)
def add_group_member(
    data: GroupMemberRequest,
    current_user: dict = Depends(get_current_user),
):
    if data.group_id not in groups_db:
        raise HTTPException(status_code=404, detail="Group not found")

    members = group_members_db.setdefault(data.group_id, [])
    if data.user_email not in members:
        members.append(data.user_email)
    return {"message": "Member added"}


@router.delete("/member", status_code=204)
def remove_group_member(
    data: GroupMemberRequest,
    current_user: dict = Depends(get_current_user),
):
    members = group_members_db.get(data.group_id)
    if members and data.user_email in members:
        members.remove(data.user_email)
    return None


@router.get("/members", response_model=GroupMembersResponse)
def get_group_members(
    group_id: str,
    current_user: dict = Depends(get_current_user),
):
    if group_id not in groups_db:
        raise HTTPException(status_code=404, detail="Group not found")

    return GroupMembersResponse(
        group_id=group_id,
        members=group_members_db.get(group_id, []),
    )


@router.post("/search", response_model=list[GroupResponse])
def search_groups(
    data: GroupSearchRequest,
    current_user: dict = Depends(get_current_user),
):
    query_lower = data.query.lower()
    return [g for g in groups_db.values() if query_lower in g["name"].lower()]


# ─── Dynamic /{group_id} routes come LAST ───

@router.patch("/{group_id}", response_model=GroupResponse)
def update_group(
    group_id: str,
    data: GroupUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    group = groups_db.get(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    if data.name is not None:
        group["name"] = data.name
    if data.description is not None:
        group["description"] = data.description
    return group


@router.delete("/{group_id}", status_code=204)
def delete_group(
    group_id: str,
    current_user: dict = Depends(get_current_user),
):
    if group_id not in groups_db:
        raise HTTPException(status_code=404, detail="Group not found")

    del groups_db[group_id]
    group_members_db.pop(group_id, None)
    return None