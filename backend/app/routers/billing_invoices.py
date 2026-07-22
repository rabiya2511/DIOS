"""
Invoices router — list unpaid, generate, download, pay, history.
Matches the Invoices section of the Billing APIs blueprint (5/5).
GET /invoices returns outstanding (unpaid) invoices; GET /invoices/history
returns paid ones — a meaningful split rather than duplicating the same
list. Paying an invoice creates a real entry in billing_payments.py's
payments_db, so it also shows up in GET /billing/payments/history.
"""

import io
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas.billing_invoices import (
    InvoiceGenerateRequest,
    InvoiceResponse,
    InvoiceDownloadRequest,
    InvoicePayRequest,
)
from app.routers.billing_payments import payments_db
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/billing", tags=["Billing Invoices"])

# id -> {id, customer_email, items, amount, currency, status, created_at, paid_at}
invoices_db: dict[str, dict] = {}


def _get_own_invoice_or_404(invoice_id: str, email: str) -> dict:
    invoice = invoices_db.get(invoice_id)
    if not invoice or invoice["customer_email"] != email:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.get("/invoices", response_model=list[InvoiceResponse])
def list_unpaid_invoices(current_user: dict = Depends(get_current_user)):
    return [
        inv for inv in invoices_db.values()
        if inv["customer_email"] == current_user["email"] and inv["status"] == "unpaid"
    ]


@router.get("/invoices/history", response_model=list[InvoiceResponse])
def get_invoice_history(current_user: dict = Depends(get_current_user)):
    return [
        inv for inv in invoices_db.values()
        if inv["customer_email"] == current_user["email"] and inv["status"] == "paid"
    ]


@router.post("/invoices/generate", response_model=InvoiceResponse, status_code=201)
def generate_invoice(
    data: InvoiceGenerateRequest,
    current_user: dict = Depends(get_current_user),
):
    if not data.items:
        raise HTTPException(status_code=422, detail="Invoice must have at least one line item")

    invoice_id = str(uuid4())
    now = datetime.now(timezone.utc)
    total = round(sum(item.amount for item in data.items), 2)
    invoices_db[invoice_id] = {
        "id": invoice_id,
        "customer_email": current_user["email"],
        "items": [item.model_dump() for item in data.items],
        "amount": total,
        "currency": data.currency,
        "status": "unpaid",
        "created_at": now,
        "paid_at": None,
    }
    return invoices_db[invoice_id]


@router.post("/invoices/download")
def download_invoice(
    data: InvoiceDownloadRequest,
    current_user: dict = Depends(get_current_user),
):
    invoice = _get_own_invoice_or_404(data.invoice_id, current_user["email"])

    lines = [
        f"Invoice: {invoice['id']}",
        f"Customer: {invoice['customer_email']}",
        f"Status: {invoice['status']}",
        f"Date: {invoice['created_at'].isoformat()}",
        "",
        "Items:",
    ]
    for item in invoice["items"]:
        lines.append(f"  - {item['description']}: {item['amount']:.2f} {invoice['currency']}")
    lines.append("")
    lines.append(f"Total: {invoice['amount']:.2f} {invoice['currency']}")

    buffer = io.StringIO("\n".join(lines))
    return StreamingResponse(
        buffer,
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename=invoice_{invoice['id']}.txt"},
    )


@router.post("/invoices/pay", response_model=InvoiceResponse)
def pay_invoice(
    data: InvoicePayRequest,
    current_user: dict = Depends(get_current_user),
):
    invoice = _get_own_invoice_or_404(data.invoice_id, current_user["email"])
    if invoice["status"] == "paid":
        raise HTTPException(status_code=400, detail="Invoice has already been paid")

    now = datetime.now(timezone.utc)
    invoice["status"] = "paid"
    invoice["paid_at"] = now

    # create a real payment record so this also appears in payment history
    payment_id = str(uuid4())
    payments_db[payment_id] = {
        "id": payment_id,
        "customer_email": current_user["email"],
        "amount": invoice["amount"],
        "currency": invoice["currency"],
        "status": "succeeded",
        "method_id": data.method_id,
        "description": f"Payment for invoice {invoice['id']}",
        "created_at": now,
    }

    return invoice