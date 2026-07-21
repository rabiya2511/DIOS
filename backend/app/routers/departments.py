"""
Departments router — CRUD.
Matches the Departments portion of the Groups & Departments section
of the User & Organization blueprint (4/4).
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.departments import (
    DepartmentCreateRequest,
    DepartmentUpdateRequest,
    DepartmentOut,
)
from app.models.user import departments_db
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/departments", tags=["Departments"])


def _get_owned_department(department_id: str, current_user: dict) -> dict:
    dept = departments_db.get(department_id)
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    if dept["creator_email"] != current_user["email"]:
        raise HTTPException(status_code=403, detail="Only the department creator can perform this action")
    return dept


@router.get("", response_model=list[DepartmentOut])
def list_departments(org_id: str, current_user: dict = Depends(get_current_user)):
    return [d for d in departments_db.values() if d["org_id"] == org_id]


@router.post("", response_model=DepartmentOut, status_code=201)
def create_department(
    data: DepartmentCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    department_id = str(uuid4())
    department = {
        "id": department_id,
        "org_id": data.org_id,
        "name": data.name,
        "creator_email": current_user["email"],
        "created_at": datetime.now(timezone.utc),
    }
    departments_db[department_id] = department
    return department


@router.patch("/{department_id}", response_model=DepartmentOut)
def update_department(
    department_id: str,
    data: DepartmentUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    dept = _get_owned_department(department_id, current_user)
    if data.name is not None:
        dept["name"] = data.name
    return dept


@router.delete("/{department_id}", status_code=204)
def delete_department(
    department_id: str,
    current_user: dict = Depends(get_current_user),
):
    _get_owned_department(department_id, current_user)
    del departments_db[department_id]
    return None