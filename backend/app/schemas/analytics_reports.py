"""
Pydantic schemas for the Analytics: Reports domain.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ReportCreateRequest(BaseModel):
    name: str
    type: str  # e.g. "usage", "billing", "activity"
    filters: dict = {}


class ReportOut(BaseModel):
    id: str
    name: str
    type: str
    filters: dict
    owner_email: str
    schedule: Optional[str] = None
    created_at: datetime


class ReportGenerateRequest(BaseModel):
    report_id: str


class ReportRunOut(BaseModel):
    id: str
    report_id: str
    result: dict
    generated_at: datetime


class ReportScheduleRequest(BaseModel):
    report_id: str
    schedule: str  # e.g. "daily", "weekly", "monthly"


class ReportExportRequest(BaseModel):
    report_id: str