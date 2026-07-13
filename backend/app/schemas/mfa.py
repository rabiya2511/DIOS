"""
Pydantic schemas for the MFA (Multi-Factor Authentication) domain.
"""

from pydantic import BaseModel


class MFASetupResponse(BaseModel):
    secret: str              # TOTP secret (base32) — shown once for manual entry
    qr_code_base64: str      # QR code image, base64-encoded PNG, for scanning
    otpauth_url: str         # otpauth:// URI used to generate the QR code


class MFAVerifyRequest(BaseModel):
    code: str                 # 6-digit code from authenticator app


class MFAEnableRequest(BaseModel):
    code: str                 # confirm one more time before flipping MFA on


class MFADisableRequest(BaseModel):
    password: str              # require password to disable, for security


class MFARecoveryRequest(BaseModel):
    email: str
    backup_code: str


class MFAMethodsResponse(BaseModel):
    totp_enabled: bool
    backup_codes_remaining: int


class MFAChallengeRequest(BaseModel):
    email: str
    code: str


class MFABackupCodesResponse(BaseModel):
    backup_codes: list[str]   # freshly generated, shown once