"""
Role Assignments router — create, delete, list, bulk create/delete, history,
plus /users/{id}/roles, /roles/{id}/users, /roles/{id}/assign, /roles/{id}/unassign.
Matches the Role Assignments section of the Authorization APIs blueprint (10/10).
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.role_assignments import (
    RoleAssignmentCreateRequest,
    RoleAssignmentResponse,
    RoleAssignRequest,
    RoleUnassignRequest,
    RoleAssignmentBulkCreateRequest,
    RoleAssignmentBulkResult,
    RoleAssignmentBulkCreateResponse,
    RoleAssignmentBulkDeleteRequest,
    RoleAssignmentBulkDeleteResponse,
    RoleAssignmentHistoryEntry,
)
from app.models.user import users_db, roles_db
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1", tags=["Role Assignments"])

# id -> {id, user_id, role_id, assigned_at}
role_assignments_db: dict[str, dict] = {}

# append-only audit log
assignment_history_db: list[dict] = []


def _find_user_by_id(user_id: str) -> dict:
    for user in users_db.values():
        if user["id"] == user_id:
            return user
    raise HTTPException(status_code=404, detail="User not found")


def _find_role_by_id(role_id: str) -> dict:
    role = roles_db.get(role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return role


def _existing_assignment(user_id: str, role_id: str) -> dict | None:
    for a in role_assignments_db.values():
        if a["user_id"] == user_id and a["role_id"] == role_id:
            return a
    return None


def _log_history(assignment_id: str, user_id: str, role_id: str, action: str):
    assignment_history_db.append(
        {
            "assignment_id": assignment_id,
            "user_id": user_id,
            "role_id": role_id,
            "action": action,
            "timestamp": datetime.now(timezone.utc),
        }
    )


def _create_assignment(user_id: str, role_id: str) -> dict:
    _find_user_by_id(user_id)
    _find_role_by_id(role_id)
    if _existing_assignment(user_id, role_id):
        raise HTTPException(status_code=409, detail="This role is already assigned to this user")

    assignment_id = str(uuid4())
    now = datetime.now(timezone.utc)
    role_assignments_db[assignment_id] = {
        "id": assignment_id,
        "user_id": user_id,
        "role_id": role_id,
        "assigned_at": now,
    }
    _log_history(assignment_id, user_id, role_id, "assigned")
    return role_assignments_db[assignment_id]


def _delete_assignment(assignment_id: str) -> bool:
    a = role_assignments_db.get(assignment_id)
    if not a:
        return False
    _log_history(assignment_id, a["user_id"], a["role_id"], "unassigned")
    del role_assignments_db[assignment_id]
    return True


@router.post("/role-assignments", response_model=RoleAssignmentResponse, status_code=201)
def create_role_assignment(
    data: RoleAssignmentCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    return _create_assignment(data.user_id, data.role_id)


@router.get("/role-assignments", response_model=list[RoleAssignmentResponse])
def list_role_assignments(current_user: dict = Depends(get_current_user)):
    return list(role_assignments_db.values())


@router.get("/role-assignments/history", response_model=list[RoleAssignmentHistoryEntry])
def get_assignment_history(current_user: dict = Depends(get_current_user)):
    return list(assignment_history_db)


@router.post("/role-assignments/bulk", response_model=RoleAssignmentBulkCreateResponse)
def bulk_create_assignments(
    data: RoleAssignmentBulkCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    results = []
    for item in data.assignments:
        try:
            _create_assignment(item.user_id, item.role_id)
            results.append(
                RoleAssignmentBulkResult(user_id=item.user_id, role_id=item.role_id, success=True)
            )
        except HTTPException as e:
            results.append(
                RoleAssignmentBulkResult(
                    user_id=item.user_id, role_id=item.role_id, success=False, detail=e.detail
                )
            )
    return RoleAssignmentBulkCreateResponse(results=results)


@router.delete("/role-assignments/bulk", response_model=RoleAssignmentBulkDeleteResponse)
def bulk_delete_assignments(
    data: RoleAssignmentBulkDeleteRequest,
    current_user: dict = Depends(get_current_user),
):
    deleted = 0
    not_found = 0
    for assignment_id in data.assignment_ids:
        if _delete_assignment(assignment_id):
            deleted += 1
        else:
            not_found += 1
    return RoleAssignmentBulkDeleteResponse(deleted=deleted, not_found=not_found)


@router.delete("/role-assignments/{id}", status_code=204)
def delete_role_assignment(id: str, current_user: dict = Depends(get_current_user)):
    if not _delete_assignment(id):
        raise HTTPException(status_code=404, detail="Role assignment not found")
    return None


@router.get("/users/{id}/roles", response_model=list[RoleAssignmentResponse])
def get_user_roles(id: str, current_user: dict = Depends(get_current_user)):
    _find_user_by_id(id)
    return [a for a in role_assignments_db.values() if a["user_id"] == id]


@router.get("/roles/{id}/users", response_model=list[RoleAssignmentResponse])
def get_role_users(id: str, current_user: dict = Depends(get_current_user)):
    _find_role_by_id(id)
    return [a for a in role_assignments_db.values() if a["role_id"] == id]


@router.post("/roles/{id}/assign", response_model=RoleAssignmentResponse, status_code=201)
def assign_role(
    id: str,
    data: RoleAssignRequest,
    current_user: dict = Depends(get_current_user),
):
    return _create_assignment(data.user_id, id)


@router.post("/roles/{id}/unassign", status_code=204)
def unassign_role(
    id: str,
    data: RoleUnassignRequest,
    current_user: dict = Depends(get_current_user),
):
    a = _existing_assignment(data.user_id, id)
    if not a:
        raise HTTPException(status_code=404, detail="This role is not assigned to this user")
    _delete_assignment(a["id"])
    return None