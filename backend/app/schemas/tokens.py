"""
Pydantic schemas for the Tokens domain (API keys / long-lived tokens,
distinct from the login access/refresh JWTs issued by /auth).
STUBBED: token secrets are random strings, not signed JWTs.
"""

from datetime import datetime

from pydantic import BaseModel


class TokenCreateRequest(BaseModel):
    name: str  # e.g. "CI pipeline", "Zapier integration"


class TokenCreateResponse(BaseModel):
    id: str
    name: str
    token: str  # raw secret — shown once, at creation only
    created_at: datetime


class TokenRefreshRequest(BaseModel):
    id: str


class TokenRefreshResponse(BaseModel):
    id: str
    token: str  # new raw secret — shown once
    created_at: datetime


class TokenRevokeRequest(BaseModel):
    id: str


class TokenListItem(BaseModel):
    id: str
    name: str
    created_at: datetime
    revoked: bool


class TokenIntrospectRequest(BaseModel):
    token: str


class TokenIntrospectResponse(BaseModel):
    active: bool
    id: str | None = None
    name: str | None = None
    email: str | None = None
    created_at: datetime | None = None