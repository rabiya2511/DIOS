"""
Pydantic schemas for the Service Accounts domain.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ServiceAccountCreateRequest(BaseModel):
    name: str


class ServiceAccountUpdateRequest(BaseModel):
    name: Optional[str] = None
    active: Optional[bool] = None


class ServiceAccountOut(BaseModel):
    id: str
    name: str
    owner_email: str
    active: bool
    created_at: datetime