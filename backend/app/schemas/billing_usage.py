"""
Pydantic schemas for the Billing: Usage & Credits domain.
"""

from pydantic import BaseModel


class UsageOut(BaseModel):
    total_requests: int
    period: str


class TokenUsageOut(BaseModel):
    total_tokens: int
    input_tokens: int
    output_tokens: int
    period: str


class CostsOut(BaseModel):
    total_cost_usd: float
    breakdown: dict[str, float]


class CreditsAddRequest(BaseModel):
    amount: float


class CreditsOut(BaseModel):
    balance: float