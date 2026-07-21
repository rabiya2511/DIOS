"""
Pydantic schemas for the Departments domain.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DepartmentCreateRequest(BaseModel):
    org_id: str
    name: str


class DepartmentUpdateRequest(BaseModel):
    name: Optional[str] = None


class DepartmentOut(BaseModel):
    id: str
    org_id: str
    name: str
    creator_email: str
    created_at: datetime