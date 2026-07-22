"""
Pydantic schemas for the Billing: Administration domain.
"""

from typing import Optional

from pydantic import BaseModel


class BillingMetricsOut(BaseModel):
    total_users_with_credits: int
    total_credits_issued: float


class BillingHealthOut(BaseModel):
    status: str
    currency: str


class BillingConfigOut(BaseModel):
    currency: str
    tax_rate_percent: float
    auto_billing_enabled: bool


class BillingConfigUpdateRequest(BaseModel):
    currency: Optional[str] = None
    tax_rate_percent: Optional[float] = None
    auto_billing_enabled: Optional[bool] = None


class BillingAuditEntryOut(BaseModel):
    actor_email: str
    action: str
    timestamp: str