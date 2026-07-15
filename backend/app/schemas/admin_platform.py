"""
Pydantic schemas for the Platform Configuration admin domain.
"""

from typing import Optional

from pydantic import BaseModel


class PlatformConfigOut(BaseModel):
    site_name: str
    support_email: str
    maintenance_mode: bool


class PlatformConfigUpdateRequest(BaseModel):
    site_name: Optional[str] = None
    support_email: Optional[str] = None
    maintenance_mode: Optional[bool] = None


class FeatureFlagsOut(BaseModel):
    new_dashboard: bool
    beta_api_access: bool
    dark_mode: bool


class FeatureFlagsUpdateRequest(BaseModel):
    new_dashboard: Optional[bool] = None
    beta_api_access: Optional[bool] = None
    dark_mode: Optional[bool] = None


class LicensesOut(BaseModel):
    plan: str
    seats: int
    seats_used: int
    expires_at: str


class BrandingOut(BaseModel):
    logo_url: str
    primary_color: str
    company_name: str


class BrandingUpdateRequest(BaseModel):
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    company_name: Optional[str] = None