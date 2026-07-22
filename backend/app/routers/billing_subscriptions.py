"""
Subscriptions router — plans, create, update, upgrade, cancel.
Matches the Subscriptions section of the Billing APIs blueprint (5/5).
DELETE performs a soft-cancel (status -> "cancelled") rather than a hard
delete, matching standard billing practice of preserving subscription
history.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.billing_subscriptions import (
    PlanResponse,
    SubscriptionCreateRequest,
    SubscriptionUpdateRequest,
    SubscriptionUpgradeRequest,
    SubscriptionResponse,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/billing", tags=["Billing Subscriptions"])

# id -> {id, name, price_monthly, currency, features}
plans_db: dict[str, dict] = {}

# id -> {id, customer_email, plan_id, status, started_at, updated_at}
subscriptions_db: dict[str, dict] = {}


def _seed_plans():
    if plans_db:
        return
    for name, price, features in [
        ("Free", 0.0, ["1 project", "Community support"]),
        ("Pro", 29.0, ["Unlimited projects", "Priority support", "API access"]),
        ("Enterprise", 199.0, ["Unlimited everything", "Dedicated support", "SSO", "SLA"]),
    ]:
        plan_id = str(uuid4())
        plans_db[plan_id] = {
            "id": plan_id,
            "name": name,
            "price_monthly": price,
            "currency": "USD",
            "features": features,
        }


_seed_plans()


def _get_plan_or_404(plan_id: str) -> dict:
    plan = plans_db.get(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


def _get_subscription_or_404(id: str) -> dict:
    sub = subscriptions_db.get(id)
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return sub


@router.get("/plans", response_model=list[PlanResponse])
def list_plans():
    return list(plans_db.values())


@router.post("/subscriptions", response_model=SubscriptionResponse, status_code=201)
def create_subscription(
    data: SubscriptionCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    _get_plan_or_404(data.plan_id)
    sub_id = str(uuid4())
    now = datetime.now(timezone.utc)
    subscriptions_db[sub_id] = {
        "id": sub_id,
        "customer_email": current_user["email"],
        "plan_id": data.plan_id,
        "status": "active",
        "started_at": now,
        "updated_at": now,
    }
    return subscriptions_db[sub_id]


@router.patch("/subscriptions/{id}", response_model=SubscriptionResponse)
def update_subscription(
    id: str,
    data: SubscriptionUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    sub = _get_subscription_or_404(id)
    if data.plan_id is not None:
        _get_plan_or_404(data.plan_id)
        sub["plan_id"] = data.plan_id
    if data.status is not None:
        sub["status"] = data.status
    sub["updated_at"] = datetime.now(timezone.utc)
    return sub


@router.post("/subscriptions/upgrade", response_model=SubscriptionResponse)
def upgrade_subscription(
    data: SubscriptionUpgradeRequest,
    current_user: dict = Depends(get_current_user),
):
    sub = _get_subscription_or_404(data.subscription_id)
    _get_plan_or_404(data.new_plan_id)
    sub["plan_id"] = data.new_plan_id
    sub["updated_at"] = datetime.now(timezone.utc)
    return sub


@router.delete("/subscriptions/{id}", response_model=SubscriptionResponse)
def cancel_subscription(id: str, current_user: dict = Depends(get_current_user)):
    sub = _get_subscription_or_404(id)
    sub["status"] = "cancelled"
    sub["updated_at"] = datetime.now(timezone.utc)
    return sub