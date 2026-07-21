"""
Admin router — User & Access Administration.
Matches section 1 of the Administration blueprint (6/6).
All endpoints require admin privileges.
"""

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.admin_users import (
    AdminUserOut,
    AdminUserUpdateRequest,
    AdminUserActionRequest,
    AdminResetPasswordResponse,
    AdminUserActivityOut,
    ImpersonateResponse,
    EndImpersonationRequest,
)
from app.models.user import users_db, password_reset_tokens_db, login_history_db,impersonation_sessions_db
from app.core.security import get_current_admin,create_access_token

router = APIRouter(prefix="/api/v1/admin/users", tags=["Admin: Users"])


def _to_admin_user_out(user: dict) -> dict:
    return {
        "id": user["id"],
        "email": user["email"],
        "full_name": user["full_name"],
        "created_at": user["created_at"],
        "is_admin": user.get("is_admin", False),
        "suspended": user.get("suspended", False),
    }


@router.get("", response_model=list[AdminUserOut])
def list_users(current_admin: dict = Depends(get_current_admin)):
    return [_to_admin_user_out(u) for u in users_db.values()]


@router.patch("/{user_id}", response_model=AdminUserOut)
def update_user(
    user_id: str,
    data: AdminUserUpdateRequest,
    current_admin: dict = Depends(get_current_admin),
):
    user = next((u for u in users_db.values() if u["id"] == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if data.full_name is not None:
        user["full_name"] = data.full_name
    if data.is_admin is not None:
        user["is_admin"] = data.is_admin

    return _to_admin_user_out(user)


@router.post("/suspend", status_code=204)
def suspend_user(
    data: AdminUserActionRequest,
    current_admin: dict = Depends(get_current_admin),
):
    user = users_db.get(data.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user["suspended"] = True
    return None


@router.post("/activate", status_code=204)
def activate_user(
    data: AdminUserActionRequest,
    current_admin: dict = Depends(get_current_admin),
):
    user = users_db.get(data.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user["suspended"] = False
    return None


@router.post("/reset-password", response_model=AdminResetPasswordResponse)
def admin_reset_password(
    data: AdminUserActionRequest,
    current_admin: dict = Depends(get_current_admin),
):
    if data.email not in users_db:
        raise HTTPException(status_code=404, detail="User not found")

    reset_token = str(uuid4())
    password_reset_tokens_db[reset_token] = data.email

    return AdminResetPasswordResponse(
        message="Password reset token generated for user.",
        reset_token=reset_token,  # TEMP: normally emailed, not returned
    )


@router.get("/activity", response_model=list[AdminUserActivityOut])
def get_user_activity(current_admin: dict = Depends(get_current_admin)):
    activity = []
    for email, entries in login_history_db.items():
        for entry in entries:
            activity.append({
                "email": email,
                "success": entry["success"],
                "ip": entry["ip"],
                "timestamp": entry["timestamp"],
            })
    activity.sort(key=lambda x: x["timestamp"], reverse=True)
    return activity
@router.post("/lock", status_code=204)
def lock_user(
    data: AdminUserActionRequest,
    current_admin: dict = Depends(get_current_admin),
):
    user = users_db.get(data.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user["locked"] = True
    return None


@router.post("/unlock", status_code=204)
def unlock_user(
    data: AdminUserActionRequest,
    current_admin: dict = Depends(get_current_admin),
):
    user = users_db.get(data.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user["locked"] = False
    return None


@router.post("/impersonate", response_model=ImpersonateResponse)
def impersonate_user(
    data: AdminUserActionRequest,
    current_admin: dict = Depends(get_current_admin),
):
    target = users_db.get(data.email)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    impersonation_token = create_access_token(target["email"])
    impersonation_sessions_db[impersonation_token] = current_admin["email"]

    return ImpersonateResponse(
        access_token=impersonation_token,
        impersonated_email=target["email"],
        message=f"Now impersonating {target['email']}. Use this token for requests; call end-impersonation when done.",
    )


@router.post("/end-impersonation", status_code=204)
def end_impersonation(data: EndImpersonationRequest):
    if data.access_token not in impersonation_sessions_db:
        raise HTTPException(status_code=400, detail="This token is not an active impersonation session")
    del impersonation_sessions_db[data.access_token]
    return None