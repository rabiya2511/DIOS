"""
Service Accounts router — create, list, update, delete.
Matches the Service Accounts section of the Auth blueprint (4/4).
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.service_accounts import (
    ServiceAccountCreateRequest,
    ServiceAccountUpdateRequest,
    ServiceAccountOut,
)
from app.models.user import service_accounts_db
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/service-accounts", tags=["Service Accounts"])


@router.post("", response_model=ServiceAccountOut, status_code=201)
def create_service_account(
    data: ServiceAccountCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    account_id = str(uuid4())
    account = {
        "id": account_id,
        "name": data.name,
        "owner_email": current_user["email"],
        "active": True,
        "created_at": datetime.now(timezone.utc),
    }
    service_accounts_db[account_id] = account
    return account


@router.get("", response_model=list[ServiceAccountOut])
def list_service_accounts(current_user: dict = Depends(get_current_user)):
    email = current_user["email"]
    return [acc for acc in service_accounts_db.values() if acc["owner_email"] == email]


@router.patch("/{account_id}", response_model=ServiceAccountOut)
def update_service_account(
    account_id: str,
    data: ServiceAccountUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    account = service_accounts_db.get(account_id)
    if not account or account["owner_email"] != current_user["email"]:
        raise HTTPException(status_code=404, detail="Service account not found")

    if data.name is not None:
        account["name"] = data.name
    if data.active is not None:
        account["active"] = data.active

    return account


@router.delete("/{account_id}", status_code=204)
def delete_service_account(
    account_id: str,
    current_user: dict = Depends(get_current_user),
):
    account = service_accounts_db.get(account_id)
    if not account or account["owner_email"] != current_user["email"]:
        raise HTTPException(status_code=404, detail="Service account not found")

    del service_accounts_db[account_id]
    return None