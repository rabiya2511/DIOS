"""
Pydantic schemas for the Analytics: Dashboards domain.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class WidgetCreateRequest(BaseModel):
    title: str
    type: str  # e.g. "chart", "metric", "table"
    config: dict = {}


class WidgetUpdateRequest(BaseModel):
    title: Optional[str] = None
    config: Optional[dict] = None


class WidgetOut(BaseModel):
    id: str
    title: str
    type: str
    config: dict
    created_at: datetime


class DashboardOut(BaseModel):
    owner_email: str
    widgets: list[WidgetOut]


class OverviewOut(BaseModel):
    total_users: int
    total_projects: int
    total_organizations: int