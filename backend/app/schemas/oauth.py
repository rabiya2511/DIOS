"""
Pydantic schemas for the OAuth domain.
STUBBED: real provider token exchange comes later, per provider.
"""

from pydantic import BaseModel


class OAuthLoginRequest(BaseModel):
    auth_code: str   # stubbed — in the stub, this doubles as the user's email


class OAuthDisconnectRequest(BaseModel):
    provider: str    # e.g. "google", "github"


class OAuthProvidersResponse(BaseModel):
    connected_providers: list[str]