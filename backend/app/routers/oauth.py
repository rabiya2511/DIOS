"""
OAuth router — google, github, microsoft, apple, linkedin, facebook,
disconnect, providers. Matches the OAuth section of the Auth blueprint (8/8).
STUBBED: real provider credentials/token exchange come later, per provider.
In the stub, auth_code is treated as the user's email for simplicity.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.oauth import (
    OAuthLoginRequest,
    OAuthDisconnectRequest,
    OAuthProvidersResponse,
)
from app.schemas.auth import TokenResponse
from app.models.user import users_db, oauth_connections_db
from app.core.security import create_access_token, create_refresh_token, get_current_user

router = APIRouter(prefix="/api/v1/oauth", tags=["OAuth"])

SUPPORTED_PROVIDERS = ["google", "github", "microsoft", "apple", "linkedin", "facebook"]


def _oauth_login(provider: str, data: OAuthLoginRequest) -> TokenResponse:
    # STUB: real provider token exchange + identity verification goes here later.
    email = data.auth_code
    if not email:
        raise HTTPException(status_code=401, detail=f"{provider.title()} login failed")

    if email not in users_db:
        users_db[email] = {
            "id": str(uuid4()),
            "email": email,
            "full_name": email.split("@")[0],
            "hashed_password": "",  # OAuth users have no local password
            "created_at": datetime.now(timezone.utc),
            "email_verified": True,
        }

    connections = oauth_connections_db.setdefault(email, {})
    connections[provider] = f"{provider}_stub_id_{email}"

    access_token = create_access_token(email)
    refresh_token = create_refresh_token(email)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/google", response_model=TokenResponse)
def oauth_google(data: OAuthLoginRequest):
    return _oauth_login("google", data)


@router.post("/github", response_model=TokenResponse)
def oauth_github(data: OAuthLoginRequest):
    return _oauth_login("github", data)


@router.post("/microsoft", response_model=TokenResponse)
def oauth_microsoft(data: OAuthLoginRequest):
    return _oauth_login("microsoft", data)


@router.post("/apple", response_model=TokenResponse)
def oauth_apple(data: OAuthLoginRequest):
    return _oauth_login("apple", data)


@router.post("/linkedin", response_model=TokenResponse)
def oauth_linkedin(data: OAuthLoginRequest):
    return _oauth_login("linkedin", data)


@router.post("/facebook", response_model=TokenResponse)
def oauth_facebook(data: OAuthLoginRequest):
    return _oauth_login("facebook", data)


@router.post("/disconnect", status_code=204)
def oauth_disconnect(
    data: OAuthDisconnectRequest,
    current_user: dict = Depends(get_current_user),
):
    email = current_user["email"]
    connections = oauth_connections_db.get(email, {})
    if data.provider not in connections:
        raise HTTPException(status_code=400, detail=f"{data.provider.title()} is not connected")

    del connections[data.provider]
    return None


@router.get("/providers", response_model=OAuthProvidersResponse)
def oauth_providers(current_user: dict = Depends(get_current_user)):
    email = current_user["email"]
    connected = list(oauth_connections_db.get(email, {}).keys())
    return OAuthProvidersResponse(connected_providers=connected)