"""
API Keys router — create, list, update (PATCH), delete, rotate, revoke.
Matches the API Keys section of the Auth blueprint (6/6).
STUBBED: raw secrets are random hex strings; only a hash is retained
after creation. A short prefix stays visible for identification in a UI.
"""

import hashlib
import secrets
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.api_keys import (
    ApiKeyCreateRequest,
    ApiKeyCreateResponse,
    ApiKeyUpdateRequest,
    ApiKeyListItem,
    ApiKeyRotateRequest,
    ApiKeyRotateResponse,
    ApiKeyRevokeRequest,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/api-keys", tags=["API Keys"])

# id -> {id, email, name, scopes, prefix, key_hash, created_at, revoked}
api_keys_db: dict[str, dict] = {}


def _hash(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


def _generate_raw_key() -> tuple[str, str]:
    raw = f"sk_{secrets.token_hex(24)}"
    prefix = raw[:11]  # "sk_" + first 8 hex chars
    return raw, prefix


def _get_owned_key_or_404(id: str, email: str) -> dict:
    record = api_keys_db.get(id)
    if not record or record["email"] != email:
        raise HTTPException(status_code=404, detail="API key not found")
    return record


@router.post("", response_model=ApiKeyCreateResponse, status_code=201)
def create_api_key(data: ApiKeyCreateRequest, current_user: dict = Depends(get_current_user)):
    key_id = str(uuid4())
    raw_key, prefix = _generate_raw_key()
    now = datetime.now(timezone.utc)

    api_keys_db[key_id] = {
        "id": key_id,
        "email": current_user["email"],
        "name": data.name,
        "scopes": data.scopes,
        "prefix": prefix,
        "key_hash": _hash(raw_key),
        "created_at": now,
        "revoked": False,
    }
    return ApiKeyCreateResponse(
        id=key_id, name=data.name, scopes=data.scopes, prefix=prefix, key=raw_key, created_at=now
    )


@router.get("", response_model=list[ApiKeyListItem])
def list_api_keys(current_user: dict = Depends(get_current_user)):
    return [
        ApiKeyListItem(**record)
        for record in api_keys_db.values()
        if record["email"] == current_user["email"]
    ]


@router.patch("/{id}", response_model=ApiKeyListItem)
def update_api_key(
    id: str,
    data: ApiKeyUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    record = _get_owned_key_or_404(id, current_user["email"])
    if data.name is not None:
        record["name"] = data.name
    if data.scopes is not None:
        record["scopes"] = data.scopes
    return ApiKeyListItem(**record)


@router.delete("/{id}", status_code=204)
def delete_api_key(id: str, current_user: dict = Depends(get_current_user)):
    _get_owned_key_or_404(id, current_user["email"])
    del api_keys_db[id]
    return None


@router.post("/rotate", response_model=ApiKeyRotateResponse)
def rotate_api_key(data: ApiKeyRotateRequest, current_user: dict = Depends(get_current_user)):
    record = _get_owned_key_or_404(data.id, current_user["email"])
    if record["revoked"]:
        raise HTTPException(status_code=400, detail="Cannot rotate a revoked API key")

    raw_key, prefix = _generate_raw_key()
    now = datetime.now(timezone.utc)
    record["key_hash"] = _hash(raw_key)
    record["prefix"] = prefix
    record["created_at"] = now
    return ApiKeyRotateResponse(id=record["id"], prefix=prefix, key=raw_key, created_at=now)


@router.post("/revoke", status_code=204)
def revoke_api_key(data: ApiKeyRevokeRequest, current_user: dict = Depends(get_current_user)):
    record = _get_owned_key_or_404(data.id, current_user["email"])
    record["revoked"] = True
    return None