"""
MFA router — setup, verify, enable, disable, recovery, methods, challenge, backup-codes.
Matches the MFA section of the Auth blueprint (8 of 8 endpoints).
TOTP-based (Google Authenticator / Authy compatible).
"""

import base64
import secrets
from io import BytesIO

import pyotp
import qrcode
from fastapi import APIRouter, Depends, HTTPException

from app.schemas.mfa import (
    MFASetupResponse,
    MFAVerifyRequest,
    MFAEnableRequest,
    MFADisableRequest,
    MFARecoveryRequest,
    MFAMethodsResponse,
    MFAChallengeRequest,
    MFABackupCodesResponse,
)
from app.models.user import users_db, mfa_secrets_db, mfa_backup_codes_db
from app.core.security import verify_password, get_current_user

router = APIRouter(prefix="/api/v1/mfa", tags=["MFA"])

ISSUER_NAME = "DIOS"


def _generate_backup_codes(count: int = 10) -> list[str]:
    return [secrets.token_hex(4) for _ in range(count)]


@router.post("/setup", response_model=MFASetupResponse)
def setup_mfa(current_user: dict = Depends(get_current_user)):
    email = current_user["email"]
    secret = pyotp.random_base32()

    # Not confirmed yet — /verify or /enable flips this to True
    mfa_secrets_db[email] = {"secret": secret, "confirmed": False}

    totp = pyotp.TOTP(secret)
    otpauth_url = totp.provisioning_uri(name=email, issuer_name=ISSUER_NAME)

    qr_img = qrcode.make(otpauth_url)
    buffer = BytesIO()
    qr_img.save(buffer, format="PNG")
    qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()

    return MFASetupResponse(
        secret=secret,
        qr_code_base64=qr_code_base64,
        otpauth_url=otpauth_url,
    )


@router.post("/verify", status_code=204)
def verify_mfa(
    data: MFAVerifyRequest,
    current_user: dict = Depends(get_current_user),
):
    email = current_user["email"]
    entry = mfa_secrets_db.get(email)
    if not entry:
        raise HTTPException(status_code=400, detail="MFA setup not started")

    totp = pyotp.TOTP(entry["secret"])
    if not totp.verify(data.code):
        raise HTTPException(status_code=400, detail="Invalid code")

    return None


@router.post("/enable", status_code=204)
def enable_mfa(
    data: MFAEnableRequest,
    current_user: dict = Depends(get_current_user),
):
    email = current_user["email"]
    entry = mfa_secrets_db.get(email)
    if not entry:
        raise HTTPException(status_code=400, detail="MFA setup not started")

    totp = pyotp.TOTP(entry["secret"])
    if not totp.verify(data.code):
        raise HTTPException(status_code=400, detail="Invalid code")

    entry["confirmed"] = True
    # Generate initial backup codes the moment MFA turns on
    mfa_backup_codes_db[email] = _generate_backup_codes()
    return None


@router.post("/disable", status_code=204)
def disable_mfa(
    data: MFADisableRequest,
    current_user: dict = Depends(get_current_user),
):
    email = current_user["email"]
    if not verify_password(data.password, current_user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Incorrect password")

    mfa_secrets_db.pop(email, None)
    mfa_backup_codes_db.pop(email, None)
    return None


@router.post("/recovery", status_code=204)
def recover_with_backup_code(data: MFARecoveryRequest):
    codes = mfa_backup_codes_db.get(data.email, [])
    if data.backup_code not in codes:
        raise HTTPException(status_code=400, detail="Invalid or already-used backup code")

    codes.remove(data.backup_code)  # one-time use
    return None


@router.get("/methods", response_model=MFAMethodsResponse)
def get_mfa_methods(current_user: dict = Depends(get_current_user)):
    email = current_user["email"]
    entry = mfa_secrets_db.get(email)
    totp_enabled = bool(entry and entry.get("confirmed"))
    remaining = len(mfa_backup_codes_db.get(email, []))

    return MFAMethodsResponse(
        totp_enabled=totp_enabled,
        backup_codes_remaining=remaining,
    )


@router.post("/challenge", status_code=204)
def mfa_challenge(data: MFAChallengeRequest):
    entry = mfa_secrets_db.get(data.email)
    if not entry or not entry.get("confirmed"):
        raise HTTPException(status_code=400, detail="MFA not enabled for this account")

    totp = pyotp.TOTP(entry["secret"])
    if not totp.verify(data.code):
        raise HTTPException(status_code=400, detail="Invalid code")

    return None


@router.post("/backup-codes", response_model=MFABackupCodesResponse)
def regenerate_backup_codes(current_user: dict = Depends(get_current_user)):
    email = current_user["email"]
    entry = mfa_secrets_db.get(email)
    if not entry or not entry.get("confirmed"):
        raise HTTPException(status_code=400, detail="MFA not enabled for this account")

    new_codes = _generate_backup_codes()
    mfa_backup_codes_db[email] = new_codes
    return MFABackupCodesResponse(backup_codes=new_codes)