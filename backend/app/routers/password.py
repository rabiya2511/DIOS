"""
Password router — forgot, reset, change, validate, check-strength, history.
Matches the Password section of the Auth blueprint (6 of 6 endpoints).
"""

import re
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.password import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    ChangePasswordRequest,
    ValidatePasswordRequest,
    ValidatePasswordResponse,
    PasswordStrengthResponse,
    PasswordHistoryResponse,
)
from app.models.user import users_db, password_reset_tokens_db, password_history_db
from app.core.security import hash_password, verify_password, get_current_user

router = APIRouter(prefix="/api/v1/password", tags=["Password"])

HISTORY_LIMIT = 5  # how many past passwords to remember and block reuse of


def _validate_password_rules(password: str) -> list[str]:
    reasons = []
    if len(password) < 8:
        reasons.append("Password must be at least 8 characters long")
    if not re.search(r"[A-Z]", password):
        reasons.append("Password must contain at least one uppercase letter")
    if not re.search(r"[0-9]", password):
        reasons.append("Password must contain at least one number")
    return reasons


def _check_and_record_history(email: str, new_password: str, current_hashed: str) -> None:
    """Raise if new_password matches current or any recent past password; otherwise record it."""
    history = password_history_db.setdefault(email, [])

    if verify_password(new_password, current_hashed):
        raise HTTPException(status_code=422, detail=["New password must be different from your current password"])

    for old_hashed in history:
        if verify_password(new_password, old_hashed):
            raise HTTPException(status_code=422, detail=["You cannot reuse a recent password"])

    history.append(current_hashed)  # the password being replaced goes into history
    del history[:-HISTORY_LIMIT]     # keep only the most recent HISTORY_LIMIT entries


@router.post("/forgot", response_model=ForgotPasswordResponse)
def forgot_password(data: ForgotPasswordRequest):
    reset_token = str(uuid4())
    if data.email in users_db:
        password_reset_tokens_db[reset_token] = data.email

    return ForgotPasswordResponse(
        message="If that email exists, a reset link has been generated.",
        reset_token=reset_token,  # TEMP: normally this goes in an email, not the response
    )


@router.post("/reset", status_code=204)
def reset_password(data: ResetPasswordRequest):
    email = password_reset_tokens_db.get(data.reset_token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    reasons = _validate_password_rules(data.new_password)
    if reasons:
        raise HTTPException(status_code=422, detail=reasons)

    current_hashed = users_db[email]["hashed_password"]
    _check_and_record_history(email, data.new_password, current_hashed)

    users_db[email]["hashed_password"] = hash_password(data.new_password)
    del password_reset_tokens_db[data.reset_token]  # one-time use
    return None


@router.post("/change", status_code=204)
def change_password(
    data: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
):
    if not verify_password(data.old_password, current_user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Old password is incorrect")

    reasons = _validate_password_rules(data.new_password)
    if reasons:
        raise HTTPException(status_code=422, detail=reasons)

    email = current_user["email"]
    current_hashed = current_user["hashed_password"]
    _check_and_record_history(email, data.new_password, current_hashed)

    current_user["hashed_password"] = hash_password(data.new_password)
    return None


@router.post("/validate", response_model=ValidatePasswordResponse)
def validate_password(data: ValidatePasswordRequest):
    reasons = _validate_password_rules(data.password)
    return ValidatePasswordResponse(valid=len(reasons) == 0, reasons=reasons)


@router.post("/check-strength", response_model=PasswordStrengthResponse)
def check_strength(data: ValidatePasswordRequest):
    password = data.password
    score = 0
    if len(password) >= 8:
        score += 1
    if len(password) >= 12:
        score += 1
    if re.search(r"[A-Z]", password) and re.search(r"[a-z]", password):
        score += 1
    if re.search(r"[0-9]", password):
        score += 1
    if re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        score += 1

    labels = ["weak", "weak", "fair", "good", "strong", "very strong"]
    return PasswordStrengthResponse(score=min(score, 4), label=labels[score])


@router.get("/history", response_model=PasswordHistoryResponse)
def get_password_history(current_user: dict = Depends(get_current_user)):
    email = current_user["email"]
    history = password_history_db.get(email, [])
    return PasswordHistoryResponse(count=len(history), reused_blocked=0)