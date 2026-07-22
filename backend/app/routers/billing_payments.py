"""
Payments router — charge, get, refund, history, methods.
Matches the Payments section of the Billing APIs blueprint (5/5).
STUBBED: no real payment provider — charges always succeed (unless
amount <= 0).
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.billing_payments import (
    PaymentCreateRequest,
    PaymentResponse,
    PaymentRefundRequest,
    PaymentMethodResponse,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/billing", tags=["Billing Payments"])

# id -> {id, customer_email, amount, currency, status, method_id, description, created_at}
payments_db: dict[str, dict] = {}

# email -> list of {id, type, brand, last4, added_at}
payment_methods_db: dict[str, list] = {}


def _get_or_seed_methods(email: str) -> list:
    if email not in payment_methods_db:
        payment_methods_db[email] = [
            {
                "id": str(uuid4()),
                "type": "card",
                "brand": "Visa",
                "last4": "4242",
                "added_at": datetime.now(timezone.utc),
            }
        ]
    return payment_methods_db[email]


def _get_own_payment_or_404(payment_id: str, email: str) -> dict:
    payment = payments_db.get(payment_id)
    if not payment or payment["customer_email"] != email:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment


@router.post("/payments", response_model=PaymentResponse, status_code=201)
def create_payment(
    data: PaymentCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    if data.amount <= 0:
        raise HTTPException(status_code=422, detail="amount must be greater than 0")

    payment_id = str(uuid4())
    now = datetime.now(timezone.utc)
    payments_db[payment_id] = {
        "id": payment_id,
        "customer_email": current_user["email"],
        "amount": data.amount,
        "currency": data.currency,
        "status": "succeeded",  # STUB: always succeeds
        "method_id": data.method_id,
        "description": data.description,
        "created_at": now,
    }
    return payments_db[payment_id]


@router.get("/payments/history", response_model=list[PaymentResponse])
def get_payment_history(current_user: dict = Depends(get_current_user)):
    return [p for p in payments_db.values() if p["customer_email"] == current_user["email"]]


@router.get("/payments/methods", response_model=list[PaymentMethodResponse])
def get_payment_methods(current_user: dict = Depends(get_current_user)):
    return _get_or_seed_methods(current_user["email"])


@router.get("/payments/{id}", response_model=PaymentResponse)
def get_payment(id: str, current_user: dict = Depends(get_current_user)):
    return _get_own_payment_or_404(id, current_user["email"])


@router.post("/payments/refund", response_model=PaymentResponse)
def refund_payment(
    data: PaymentRefundRequest,
    current_user: dict = Depends(get_current_user),
):
    payment = _get_own_payment_or_404(data.payment_id, current_user["email"])
    if payment["status"] == "refunded":
        raise HTTPException(status_code=400, detail="Payment has already been refunded")

    payment["status"] = "refunded"
    return payment