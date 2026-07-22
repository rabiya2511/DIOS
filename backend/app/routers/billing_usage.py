"""
Billing router — Usage & Credits.
Matches the Usage & Credits section of the Billing blueprint (5/5).
Usage/tokens/costs are simulated (no real metering pipeline yet);
credits are tracked for real per user.
"""

from fastapi import APIRouter, Depends

from app.schemas.billing_usage import (
    UsageOut,
    TokenUsageOut,
    CostsOut,
    CreditsAddRequest,
    CreditsOut,
)
from app.models.user import billing_credits_db, audit_logs_db
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/billing", tags=["Billing: Usage & Credits"])


@router.get("/usage", response_model=UsageOut)
def get_usage(current_user: dict = Depends(get_current_user)):
    email = current_user["email"]
    count = sum(1 for e in audit_logs_db if e["actor_email"] == email)
    return UsageOut(total_requests=count, period="current_month")


@router.get("/usage/tokens", response_model=TokenUsageOut)
def get_token_usage(current_user: dict = Depends(get_current_user)):
    # STUB: real version reads from a token-metering pipeline.
    email = current_user["email"]
    count = sum(1 for e in audit_logs_db if e["actor_email"] == email)
    input_tokens = count * 150
    output_tokens = count * 300
    return TokenUsageOut(
        total_tokens=input_tokens + output_tokens,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        period="current_month",
    )


@router.get("/costs", response_model=CostsOut)
def get_costs(current_user: dict = Depends(get_current_user)):
    # STUB: simple simulated pricing based on usage.
    email = current_user["email"]
    count = sum(1 for e in audit_logs_db if e["actor_email"] == email)
    api_cost = round(count * 0.01, 2)
    token_cost = round(count * 450 * 0.00002, 2)
    return CostsOut(
        total_cost_usd=round(api_cost + token_cost, 2),
        breakdown={"api_requests": api_cost, "tokens": token_cost},
    )


@router.post("/credits/add", response_model=CreditsOut)
def add_credits(
    data: CreditsAddRequest,
    current_user: dict = Depends(get_current_user),
):
    email = current_user["email"]
    billing_credits_db[email] = billing_credits_db.get(email, 0.0) + data.amount
    return CreditsOut(balance=billing_credits_db[email])


@router.get("/credits", response_model=CreditsOut)
def get_credits(current_user: dict = Depends(get_current_user)):
    email = current_user["email"]
    return CreditsOut(balance=billing_credits_db.get(email, 0.0))