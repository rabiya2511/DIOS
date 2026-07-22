"""
Pydantic schemas for the Subscriptions domain (Billing APIs blueprint).
Plans are seeded at startup; subscriptions link a customer email to a
plan with a status lifecycle (active -> cancelled).
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr

SubscriptionStatus = Literal["active", "cancelled"]


class PlanResponse(BaseModel):
    id: str
    name: str
    price_monthly: float
    currency: str
    features: list[str]


class SubscriptionCreateRequest(BaseModel):
    plan_id: str


class SubscriptionUpdateRequest(BaseModel):
    plan_id: str | None = None
    status: SubscriptionStatus | None = None


class SubscriptionUpgradeRequest(BaseModel):
    subscription_id: str
    new_plan_id: str


class SubscriptionResponse(BaseModel):
    id: str
    customer_email: EmailStr
    plan_id: str
    status: SubscriptionStatus
    started_at: datetime
    updated_at: datetime