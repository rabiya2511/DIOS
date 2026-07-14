"""
Authentication router — Registration + Login & Session endpoints.
Matches sections 1 & 2 of the Auth blueprint.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Union
import secrets

from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    UserOut,
    RegisterInviteRequest,
    RegisterOrganizationRequest,
    VerifyEmailRequest,
    ResendVerificationRequest,
    ResendVerificationResponse,
    PendingRegistrationDeleteRequest,
    PasswordlessLoginRequest,
    PasswordlessLoginResponse,
    PasskeyLoginRequest,
    SSOLoginRequest,
    DeviceLoginRequest,
    DeviceLoginStartResponse,
)
from app.models.user import (
    users_db,
    refresh_tokens_db,
    email_verification_tokens_db,
    invites_db,
    organizations_db,
    passwordless_tokens_db,
    device_codes_db,
)
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    get_current_user,
)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post("/register", response_model=UserOut, status_code=201)
def register(data: RegisterRequest):
    if data.email in users_db:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = {
        "id": str(uuid4()),
        "email": data.email,
        "full_name": data.full_name,
        "hashed_password": hash_password(data.password),
        "created_at": datetime.now(timezone.utc),
    }
    users_db[data.email] = user
    return user


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest):
    user = users_db.get(data.email)
    if not user or not verify_password(data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    access_token = create_access_token(user["email"])
    refresh_token = create_refresh_token(user["email"])
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
def refresh(data: RefreshRequest):
    email = refresh_tokens_db.get(data.refresh_token)
    if not email:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    del refresh_tokens_db[data.refresh_token]  # rotate: old token dies
    new_access_token = create_access_token(email)
    new_refresh_token = create_refresh_token(email)
    return TokenResponse(access_token=new_access_token, refresh_token=new_refresh_token)


@router.post("/logout", status_code=204)
def logout(data: RefreshRequest):
    refresh_tokens_db.pop(data.refresh_token, None)
    return None


@router.get("/session", response_model=UserOut)
def session(current_user: dict = Depends(get_current_user)):
    return current_user


# ─── Registration (remaining) ───────────────────────────────

@router.post("/register/invite", response_model=UserOut, status_code=201)
def register_via_invite(data: RegisterInviteRequest):
    invite = invites_db.get(data.invite_token)
    if not invite:
        raise HTTPException(status_code=400, detail="Invalid or expired invite token")

    email = invite["email"]
    if email in users_db:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = {
        "id": str(uuid4()),
        "email": email,
        "full_name": data.full_name,
        "hashed_password": hash_password(data.password),
        "created_at": datetime.now(timezone.utc),
        "email_verified": True,  # invited users are pre-trusted
        "organization_id": invite.get("organization_id"),
        "role": invite.get("role", "member"),
    }
    users_db[email] = user
    del invites_db[data.invite_token]  # one-time use
    return user


@router.post("/register/organization", response_model=UserOut, status_code=201)
def register_organization(data: RegisterOrganizationRequest):
    if data.email in users_db:
        raise HTTPException(status_code=400, detail="Email already registered")

    org_id = str(uuid4())
    organizations_db[org_id] = {
        "id": org_id,
        "name": data.organization_name,
        "owner_email": data.email,
        "created_at": datetime.now(timezone.utc),
    }

    user = {
        "id": str(uuid4()),
        "email": data.email,
        "full_name": data.full_name,
        "hashed_password": hash_password(data.password),
        "created_at": datetime.now(timezone.utc),
        "email_verified": False,
        "organization_id": org_id,
        "role": "owner",
    }
    users_db[data.email] = user
    return user


@router.post("/verify-email", status_code=204)
def verify_email(data: VerifyEmailRequest):
    email = email_verification_tokens_db.get(data.token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")

    users_db[email]["email_verified"] = True
    del email_verification_tokens_db[data.token]  # one-time use
    return None


@router.post("/resend-verification", response_model=ResendVerificationResponse)
def resend_verification(data: ResendVerificationRequest):
    token = str(uuid4())
    if data.email in users_db:
        email_verification_tokens_db[token] = data.email

    return ResendVerificationResponse(
        message="If that email exists, a new verification link has been generated.",
        verification_token=token,  # TEMP: normally emailed, not returned
    )


@router.delete("/pending-registration", status_code=204)
def delete_pending_registration(data: PendingRegistrationDeleteRequest):
    user = users_db.get(data.email)
    if user and not user.get("email_verified", False):
        del users_db[data.email]
    return None


# ─── Login variants (remaining) ─────────────────────────────

@router.post("/login/passwordless", response_model=Union[PasswordlessLoginResponse, TokenResponse])
def login_passwordless(data: PasswordlessLoginRequest):
    if data.login_token is None:
        # Step 1: request a magic-link token
        token = str(uuid4())
        if data.email in users_db:
            passwordless_tokens_db[token] = data.email
        return PasswordlessLoginResponse(
            message="If that email exists, a login link has been generated.",
            login_token=token,  # TEMP: normally emailed, not returned
        )

    # Step 2: complete login with the token
    email = passwordless_tokens_db.get(data.login_token)
    if not email or email != data.email:
        raise HTTPException(status_code=401, detail="Invalid or expired login token")

    del passwordless_tokens_db[data.login_token]  # one-time use
    access_token = create_access_token(email)
    refresh_token = create_refresh_token(email)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/login/passkey", response_model=TokenResponse)
def login_passkey(data: PasskeyLoginRequest):
    # STUB: real WebAuthn assertion verification goes here later.
    user = users_db.get(data.email)
    if not user:
        raise HTTPException(status_code=401, detail="Passkey login failed")

    access_token = create_access_token(user["email"])
    refresh_token = create_refresh_token(user["email"])
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/login/sso", response_model=TokenResponse)
def login_sso(data: SSOLoginRequest):
    # STUB: real SSO id_token verification against the provider goes here later.
    if not data.id_token:
        raise HTTPException(status_code=401, detail="SSO login failed")

    # Simulate: id_token "contains" the email for now (stub only)
    email = data.id_token
    if email not in users_db:
        users_db[email] = {
            "id": str(uuid4()),
            "email": email,
            "full_name": email.split("@")[0],
            "hashed_password": "",  # SSO users have no local password
            "created_at": datetime.now(timezone.utc),
            "email_verified": True,
        }

    access_token = create_access_token(email)
    refresh_token = create_refresh_token(email)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/login/device", response_model=Union[DeviceLoginStartResponse, TokenResponse])
def login_device(data: DeviceLoginRequest):
    if data.device_code is None:
        # Step 1: start the device flow
        device_code = secrets.token_urlsafe(16)
        user_code = secrets.token_hex(3).upper()
        device_codes_db[device_code] = {"user_code": user_code, "email": None, "approved": False}
        return DeviceLoginStartResponse(
            device_code=device_code,
            user_code=user_code,
            verification_uri="http://127.0.0.1:8000/device",
            expires_in=600,
        )

    # Step 2: poll/complete using the device_code
    entry = device_codes_db.get(data.device_code)
    if not entry:
        raise HTTPException(status_code=400, detail="Invalid device code")
    if not entry["approved"]:
        raise HTTPException(status_code=428, detail="Authorization pending")

    email = entry["email"]
    del device_codes_db[data.device_code]
    access_token = create_access_token(email)
    refresh_token = create_refresh_token(email)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


# ─── TEMPORARY test-only helper — remove once a real device-approval UI exists ───

class _TestApproveDeviceRequest(BaseModel):
    user_code: str
    email: str


@router.post("/login/device/_test-approve", status_code=204)
def _test_approve_device(data: _TestApproveDeviceRequest):
    for code, entry in device_codes_db.items():
        if entry["user_code"] == data.user_code:
            entry["approved"] = True
            entry["email"] = data.email
            return None
    raise HTTPException(status_code=404, detail="User code not found")
