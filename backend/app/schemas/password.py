"""
Pydantic schemas for the Password domain.
"""

from pydantic import BaseModel, EmailStr


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    message: str
    reset_token: str  # TODO: remove this field once real email sending is added


class ResetPasswordRequest(BaseModel):
    reset_token: str
    new_password: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class ValidatePasswordRequest(BaseModel):
    password: str


class ValidatePasswordResponse(BaseModel):
    valid: bool
    reasons: list[str]


class PasswordStrengthResponse(BaseModel):
    score: int          # 0 (weak) to 4 (very strong)
    label: str           # "weak" / "fair" / "good" / "strong" / "very strong"
class PasswordHistoryResponse(BaseModel):
    count: int
    reused_blocked: int  # how many reuse attempts have been blocked (informational)  