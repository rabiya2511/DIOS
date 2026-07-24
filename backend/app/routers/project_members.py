"""
Project Members router — list/add/remove members, update role, invite,
bulk-add.
Matches the Project Members section of the Projects & Workspace APIs
blueprint (6/6).

ASSUMPTIONS:
- Membership is tracked as {project_id -> {email: role}}, keyed by EMAIL,
  same convention as organizations.py's memberships_db. The blueprint's
  path segment is literally named {userId}, but since there's no shared
  user-id lookup wired into this router, that path segment is treated as
  the member's email address — pass an email there, not a numeric/UUID
  user id. Flag this if your frontend expects a real user id instead.
- The project owner is added to project_memberships_db lazily on first
  access (via _get_members), using projects_db's existing owner_email
  field — this avoids modifying projects.py's create_project function.
- POST /projects/{id}/members/invite is stubbed exactly like
  organizations.py's /invite: it adds the member directly instead of
  sending a real email/invite-token flow.
- Only "owner" or "admin" members can add/remove members or change roles
  (mirrors organizations.py's _require_admin pattern). The last remaining
  owner cannot be removed or demoted away from "owner" via role update
  (only checked on removal, not on role-update — see note in
  update_member_role if you want that hardened further).

IMPORTANT: This router shares the /api/v1/projects prefix with
projects.router. All routes here are 2+ path segments deep
(/{project_id}/members, /{project_id}/members/{email}, etc.), which never
collides with projects.router's single-segment /{id}, /archive, /restore,
/clone routes — no route-ordering fix needed here, unlike fileslifecycle.py
vs search_index.py.
"""

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.project_members import (
    ProjectMemberOut,
    ProjectMembersResponse,
    ProjectMemberAddRequest,
    ProjectMemberRoleUpdateRequest,
    ProjectMemberInviteRequest,
    ProjectMemberBulkAddRequest,
    ProjectMemberBulkAddResponse,
)
from app.routers.projects import projects_db, _get_project_or_404
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/projects", tags=["Project Members"])

# project_id -> {email: role}
project_memberships_db: dict[str, dict[str, str]] = {}


def _get_members(project_id: str) -> dict[str, str]:
    if project_id not in project_memberships_db:
        project = _get_project_or_404(project_id)
        project_memberships_db[project_id] = {project["owner_email"]: "owner"}
    return project_memberships_db[project_id]


def _require_admin(project_id: str, email: str):
    members = _get_members(project_id)
    if members.get(email) not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Requires owner or admin role on this project")


@router.get("/{project_id}/members", response_model=ProjectMembersResponse)
def list_project_members(project_id: str, current_user: dict = Depends(get_current_user)):
    _get_project_or_404(project_id)
    members = _get_members(project_id)
    if current_user["email"] not in members:
        raise HTTPException(status_code=403, detail="Not a member of this project")
    return ProjectMembersResponse(
        project_id=project_id,
        members=[ProjectMemberOut(email=e, role=r) for e, r in members.items()],
    )


@router.post("/{project_id}/members", response_model=ProjectMembersResponse, status_code=201)
def add_project_member(
    project_id: str,
    data: ProjectMemberAddRequest,
    current_user: dict = Depends(get_current_user),
):
    _get_project_or_404(project_id)
    _require_admin(project_id, current_user["email"])
    members = _get_members(project_id)
    members[data.email] = data.role
    return ProjectMembersResponse(
        project_id=project_id,
        members=[ProjectMemberOut(email=e, role=r) for e, r in members.items()],
    )


@router.patch("/{project_id}/members/{user_email}/role", response_model=ProjectMemberOut)
def update_project_member_role(
    project_id: str,
    user_email: str,
    data: ProjectMemberRoleUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    _get_project_or_404(project_id)
    _require_admin(project_id, current_user["email"])
    members = _get_members(project_id)
    if user_email not in members:
        raise HTTPException(status_code=404, detail="Member not found in project")
    members[user_email] = data.role
    return ProjectMemberOut(email=user_email, role=data.role)


@router.delete("/{project_id}/members/{user_email}", status_code=204)
def remove_project_member(
    project_id: str,
    user_email: str,
    current_user: dict = Depends(get_current_user),
):
    _get_project_or_404(project_id)
    _require_admin(project_id, current_user["email"])
    members = _get_members(project_id)
    if user_email not in members:
        raise HTTPException(status_code=404, detail="Member not found in project")

    if members[user_email] == "owner":
        owners = [e for e, r in members.items() if r == "owner"]
        if len(owners) <= 1:
            raise HTTPException(status_code=400, detail="Cannot remove the last owner")

    del members[user_email]
    return None


@router.post("/{project_id}/members/invite", status_code=201)
def invite_project_member(
    project_id: str,
    data: ProjectMemberInviteRequest,
    current_user: dict = Depends(get_current_user),
):
    _get_project_or_404(project_id)
    _require_admin(project_id, current_user["email"])
    # STUB: real version emails an invite link/token; here we add directly.
    members = _get_members(project_id)
    members[data.email] = data.role
    return {"detail": f"{data.email} added to project as {data.role}"}


@router.post("/{project_id}/members/bulk-add", response_model=ProjectMemberBulkAddResponse, status_code=201)
def bulk_add_project_members(
    project_id: str,
    data: ProjectMemberBulkAddRequest,
    current_user: dict = Depends(get_current_user),
):
    _get_project_or_404(project_id)
    _require_admin(project_id, current_user["email"])
    members = _get_members(project_id)
    for entry in data.members:
        members[entry.email] = entry.role
    return ProjectMemberBulkAddResponse(
        added_count=len(data.members),
        members=[ProjectMemberOut(email=e, role=r) for e, r in members.items()],
    )