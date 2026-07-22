"""
Pydantic schemas for the Customers & Accounts domain (Billing APIs
blueprint). STUBBED: usage numbers are simulated — no real metering
pipeline exists yet.
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr


class CustomerCreateRequest(BaseModel):
    email: EmailStr
    name: str


class CustomerUpdateRequest(BaseModel):
    name: str | None = None


class CustomerResponse(BaseModel):
    id: str
    email: EmailStr
    name: str
    created_at: datetime


class AccountBalanceResponse(BaseModel):
    balance: float
    currency: str


class AccountUsageResponse(BaseModel):
    period: str
    api_calls: int
    tokens_used: int
    storage_mb: float