"""
Pydantic schemas — define exactly what shape data must be in
requests and responses. FastAPI uses these to auto-validate input
and auto-generate the /docs page.
"""

from datetime import datetime
from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    created_at: datetime
from typing import Optional, Union


class RegisterInviteRequest(BaseModel):
    invite_token: str
    password: str
    full_name: str


class RegisterOrganizationRequest(BaseModel):
    organization_name: str
    email: EmailStr
    password: str
    full_name: str


class VerifyEmailRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class ResendVerificationResponse(BaseModel):
    message: str
    verification_token: str  # TODO: remove once real email sending is added


class PendingRegistrationDeleteRequest(BaseModel):
    email: EmailStr


class PasswordlessLoginRequest(BaseModel):
    email: EmailStr
    login_token: Optional[str] = None  # omit to request a token, include to complete login


class PasswordlessLoginResponse(BaseModel):
    message: str
    login_token: str  # TODO: remove once real email/SMS sending is added


class PasskeyLoginRequest(BaseModel):
    email: EmailStr
    passkey_credential_id: str  # stubbed — real WebAuthn assertion comes later


class SSOLoginRequest(BaseModel):
    provider: str   # e.g. "okta", "azure-ad"
    id_token: str    # stubbed — real SSO token exchange comes later


class DeviceLoginRequest(BaseModel):
    device_code: Optional[str] = None  # omit to start the flow, include to complete it


class DeviceLoginStartResponse(BaseModel):
    device_code: str
    user_code: str
    verification_uri: str
    expires_in: int