"""
Customers & Accounts router — list, create, update customers, balance,
usage. Matches the Customers & Accounts section of the Billing APIs
blueprint (5/5). STUBBED: usage numbers are simulated.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.billing_customers import (
    CustomerCreateRequest,
    CustomerUpdateRequest,
    CustomerResponse,
    AccountBalanceResponse,
    AccountUsageResponse,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1", tags=["Billing Customers & Accounts"])

# id -> {id, email, name, created_at}
customers_db: dict[str, dict] = {}

# email -> {balance, currency}
account_balances_db: dict[str, dict] = {}


def _get_or_create_balance(email: str) -> dict:
    return account_balances_db.setdefault(email, {"balance": 0.0, "currency": "USD"})


@router.get("/customers", response_model=list[CustomerResponse])
def list_customers(current_user: dict = Depends(get_current_user)):
    return list(customers_db.values())


@router.post("/customers", response_model=CustomerResponse, status_code=201)
def create_customer(
    data: CustomerCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    customer_id = str(uuid4())
    now = datetime.now(timezone.utc)
    customers_db[customer_id] = {
        "id": customer_id,
        "email": data.email,
        "name": data.name,
        "created_at": now,
    }
    return customers_db[customer_id]


@router.patch("/customers/{id}", response_model=CustomerResponse)
def update_customer(
    id: str,
    data: CustomerUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    customer = customers_db.get(id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    if data.name is not None:
        customer["name"] = data.name
    return customer


@router.get("/accounts/balance", response_model=AccountBalanceResponse)
def get_balance(current_user: dict = Depends(get_current_user)):
    return _get_or_create_balance(current_user["email"])


@router.get("/accounts/usage", response_model=AccountUsageResponse)
def get_usage(current_user: dict = Depends(get_current_user)):
    # STUB: real version would aggregate from actual API call/token logs.
    return AccountUsageResponse(
        period="current_month",
        api_calls=1247,
        tokens_used=58230,
        storage_mb=12.4,
    )