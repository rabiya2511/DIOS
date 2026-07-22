"""
Billing router — Administration.
Matches the Administration section of the Billing blueprint (5/5).
All endpoints require admin privileges.
"""

import csv
import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.schemas.billing_admin import (
    BillingMetricsOut,
    BillingHealthOut,
    BillingConfigOut,
    BillingConfigUpdateRequest,
)
from app.models.user import billing_credits_db, billing_config_db, audit_logs_db
from app.core.security import get_current_admin

router = APIRouter(prefix="/api/v1/billing", tags=["Billing: Administration"])


@router.get("/metrics", response_model=BillingMetricsOut)
def get_billing_metrics(current_admin: dict = Depends(get_current_admin)):
    return BillingMetricsOut(
        total_users_with_credits=len(billing_credits_db),
        total_credits_issued=sum(billing_credits_db.values()),
    )


@router.get("/health", response_model=BillingHealthOut)
def get_billing_health(current_admin: dict = Depends(get_current_admin)):
    return BillingHealthOut(status="healthy", currency=billing_config_db["currency"])


@router.patch("/config", response_model=BillingConfigOut)
def update_billing_config(
    data: BillingConfigUpdateRequest,
    current_admin: dict = Depends(get_current_admin),
):
    updates = data.model_dump(exclude_unset=True)
    billing_config_db.update(updates)
    return billing_config_db


@router.post("/export")
def export_billing_data(current_admin: dict = Depends(get_current_admin)):
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=["email", "credit_balance"])
    writer.writeheader()
    for email, balance in billing_credits_db.items():
        writer.writerow({"email": email, "credit_balance": balance})
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=billing_export.csv"},
    )


@router.get("/audit")
def get_billing_audit(current_admin: dict = Depends(get_current_admin)):
    billing_actions = {"credits_add"}
    return [
        {"actor_email": e["actor_email"], "action": e["action"], "timestamp": e["timestamp"].isoformat()}
        for e in audit_logs_db
        if e["action"] in billing_actions
    ]