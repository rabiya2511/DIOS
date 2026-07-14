"""
Pydantic schemas for the API Keys domain.
STUBBED: raw secrets are random hex strings, not signed JWTs.
Distinct from /tokens: API keys carry named scopes and a visible prefix
for identification in a UI, geared toward machine-to-machine use.
"""

from datetime import datetime

from pydantic import BaseModel


class ApiKeyCreateRequest(BaseModel):
    name: str
    scopes: list[str] = []  # e.g. ["read:users", "write:orders"]


class ApiKeyCreateResponse(BaseModel):
    id: str
    name: str
    scopes: list[str]
    prefix: str
    key: str  # raw secret — shown once, at creation only
    created_at: datetime


class ApiKeyUpdateRequest(BaseModel):
    name: str | None = None
    scopes: list[str] | None = None


class ApiKeyListItem(BaseModel):
    id: str
    name: str
    scopes: list[str]
    prefix: str
    created_at: datetime
    revoked: bool


class ApiKeyRotateRequest(BaseModel):
    id: str


class ApiKeyRotateResponse(BaseModel):
    id: str
    prefix: str
    key: str  # new raw secret — shown once
    created_at: datetime


class ApiKeyRevokeRequest(BaseModel):
    id: str