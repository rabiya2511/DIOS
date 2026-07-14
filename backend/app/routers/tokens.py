"""
Tokens router — create, refresh, revoke, list, delete, introspect.
Matches the Tokens section of the Auth blueprint (6/6).
STUBBED: raw secrets are random hex strings; only a hash is retained
after creation, matching typical API-key UX (shown once).
"""

import hashlib
import secrets
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.tokens import (
    TokenCreateRequest,
    TokenCreateResponse,
    TokenRefreshRequest,
    TokenRefreshResponse,
    TokenRevokeRequest,
    TokenListItem,
    TokenIntrospectRequest,
    TokenIntrospectResponse,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/tokens", tags=["Tokens"])

# id -> {id, email, name, token_hash, created_at, revoked}
api_tokens_db: dict[str, dict] = {}


def _hash(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


def _generate_raw_token() -> str:
    return f"tok_{secrets.token_hex(24)}"


@router.post("/create", response_model=TokenCreateResponse, status_code=201)
def create_token(data: TokenCreateRequest, current_user: dict = Depends(get_current_user)):
    token_id = str(uuid4())
    raw_token = _generate_raw_token()
    now = datetime.now(timezone.utc)

    api_tokens_db[token_id] = {
        "id": token_id,
        "email": current_user["email"],
        "name": data.name,
        "token_hash": _hash(raw_token),
        "created_at": now,
        "revoked": False,
    }
    return TokenCreateResponse(id=token_id, name=data.name, token=raw_token, created_at=now)


@router.post("/refresh", response_model=TokenRefreshResponse)
def refresh_token(data: TokenRefreshRequest, current_user: dict = Depends(get_current_user)):
    record = api_tokens_db.get(data.id)
    if not record or record["email"] != current_user["email"]:
        raise HTTPException(status_code=404, detail="Token not found")
    if record["revoked"]:
        raise HTTPException(status_code=400, detail="Cannot refresh a revoked token")

    raw_token = _generate_raw_token()
    now = datetime.now(timezone.utc)
    record["token_hash"] = _hash(raw_token)
    record["created_at"] = now
    return TokenRefreshResponse(id=record["id"], token=raw_token, created_at=now)


@router.post("/revoke", status_code=204)
def revoke_token(data: TokenRevokeRequest, current_user: dict = Depends(get_current_user)):
    record = api_tokens_db.get(data.id)
    if not record or record["email"] != current_user["email"]:
        raise HTTPException(status_code=404, detail="Token not found")

    record["revoked"] = True
    return None


@router.get("", response_model=list[TokenListItem])
def list_tokens(current_user: dict = Depends(get_current_user)):
    return [
        TokenListItem(**record)
        for record in api_tokens_db.values()
        if record["email"] == current_user["email"]
    ]


@router.delete("/{id}", status_code=204)
def delete_token(id: str, current_user: dict = Depends(get_current_user)):
    record = api_tokens_db.get(id)
    if not record or record["email"] != current_user["email"]:
        raise HTTPException(status_code=404, detail="Token not found")

    del api_tokens_db[id]
    return None


@router.post("/introspect", response_model=TokenIntrospectResponse)
def introspect_token(data: TokenIntrospectRequest):
    # STUB: any caller may introspect — matches RFC 7662 semantics
    # (real deployments would restrict this to trusted resource servers).
    hashed = _hash(data.token)
    for record in api_tokens_db.values():
        if record["token_hash"] == hashed and not record["revoked"]:
            return TokenIntrospectResponse(
                active=True,
                id=record["id"],
                name=record["name"],
                email=record["email"],
                created_at=record["created_at"],
            )
    return TokenIntrospectResponse(active=False)