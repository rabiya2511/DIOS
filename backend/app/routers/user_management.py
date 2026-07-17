"""
User CRUD router — list, get, create, update, delete, search,
bulk-import, bulk-export. Matches the User CRUD section of the
User Management APIs blueprint (8/8). Admin-facing, reuses the same
users_db as the rest of the app (registration, login, etc.).
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.user_management import (
    UserCreateRequest,
    UserUpdateRequest,
    UserResponse,
    UserSearchRequest,
    UserBulkImportRequest,
    UserBulkImportResult,
    UserBulkImportResponse,
    UserBulkExportResponse,
)
from app.models.user import users_db
from app.core.security import hash_password, get_current_user

router = APIRouter(prefix="/api/v1/users", tags=["User CRUD"])


def _to_response(user: dict) -> dict:
    # strip password hash and any profile-only fields not part of this schema
    return {
        "id": user["id"],
        "email": user["email"],
        "full_name": user["full_name"],
        "email_verified": user.get("email_verified", False),
        "created_at": user["created_at"],
    }


def _find_user_by_id(user_id: str) -> dict:
    for user in users_db.values():
        if user["id"] == user_id:
            return user
    raise HTTPException(status_code=404, detail="User not found")


@router.get("", response_model=list[UserResponse])
def list_users(current_user: dict = Depends(get_current_user)):
    return [_to_response(u) for u in users_db.values()]


@router.get("/{id}", response_model=UserResponse)
def get_user(id: str, current_user: dict = Depends(get_current_user)):
    return _to_response(_find_user_by_id(id))


@router.post("", response_model=UserResponse, status_code=201)
def create_user(
    data: UserCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    if data.email in users_db:
        raise HTTPException(status_code=409, detail="Email already registered")
    now = datetime.now(timezone.utc)
    users_db[data.email] = {
        "id": str(uuid4()),
        "email": data.email,
        "full_name": data.full_name,
        "hashed_password": hash_password(data.password),
        "created_at": now,
        "email_verified": False,
    }
    return _to_response(users_db[data.email])


@router.patch("/{id}", response_model=UserResponse)
def update_user(
    id: str,
    data: UserUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    user = _find_user_by_id(id)
    if data.full_name is not None:
        user["full_name"] = data.full_name
    if data.email_verified is not None:
        user["email_verified"] = data.email_verified
    return _to_response(user)


@router.delete("/{id}", status_code=204)
def delete_user(id: str, current_user: dict = Depends(get_current_user)):
    user = _find_user_by_id(id)
    del users_db[user["email"]]
    return None


@router.post("/search", response_model=list[UserResponse])
def search_users(
    data: UserSearchRequest,
    current_user: dict = Depends(get_current_user),
):
    q = data.query.lower()
    return [
        _to_response(u)
        for u in users_db.values()
        if q in u["email"].lower() or q in u["full_name"].lower()
    ]


@router.post("/bulk-import", response_model=UserBulkImportResponse)
def bulk_import_users(
    data: UserBulkImportRequest,
    current_user: dict = Depends(get_current_user),
):
    results = []
    for item in data.users:
        if item.email in users_db:
            results.append(
                UserBulkImportResult(email=item.email, success=False, detail="Email already registered")
            )
            continue
        now = datetime.now(timezone.utc)
        users_db[item.email] = {
            "id": str(uuid4()),
            "email": item.email,
            "full_name": item.full_name,
            "hashed_password": hash_password(item.password),
            "created_at": now,
            "email_verified": False,
        }
        results.append(UserBulkImportResult(email=item.email, success=True))
    return UserBulkImportResponse(results=results)


@router.post("/bulk-export", response_model=UserBulkExportResponse)
def bulk_export_users(current_user: dict = Depends(get_current_user)):
    return UserBulkExportResponse(users=[_to_response(u) for u in users_db.values()])