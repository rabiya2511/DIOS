"""
Pydantic schemas for the Payments domain (Billing APIs blueprint).
STUBBED: no real payment provider — charges always succeed (unless
amount <= 0) and are logged to payments_db.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr

PaymentStatus = Literal["succeeded", "refunded"]


class PaymentCreateRequest(BaseModel):
    amount: float
    currency: str = "USD"
    method_id: str | None = None
    description: str | None = None


class PaymentResponse(BaseModel):
    id: str
    customer_email: EmailStr
    amount: float
    currency: str
    status: PaymentStatus
    method_id: str | None = None
    description: str | None = None
    created_at: datetime


class PaymentRefundRequest(BaseModel):
    payment_id: str
    amount: float | None = None  # None = full refund


class PaymentMethodResponse(BaseModel):
    id: str
    type: str
    brand: str
    last4: str
    added_at: datetime