"""
Pydantic schemas for the Invoices domain (Billing APIs blueprint).
Paying an invoice creates a real entry in billing_payments.py's
payments_db, so invoice payments also show up in payment history.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr

InvoiceStatus = Literal["unpaid", "paid"]


class InvoiceLineItem(BaseModel):
    description: str
    amount: float


class InvoiceGenerateRequest(BaseModel):
    items: list[InvoiceLineItem]
    currency: str = "USD"


class InvoiceResponse(BaseModel):
    id: str
    customer_email: EmailStr
    items: list[InvoiceLineItem]
    amount: float
    currency: str
    status: InvoiceStatus
    created_at: datetime
    paid_at: datetime | None = None


class InvoiceDownloadRequest(BaseModel):
    invoice_id: str


class InvoicePayRequest(BaseModel):
    invoice_id: str
    method_id: str | None = None