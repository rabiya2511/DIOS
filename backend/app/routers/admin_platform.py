"""
Admin router — Platform Configuration.
Matches section 3 of the Administration blueprint (6/6).
All endpoints require admin privileges.
"""

from fastapi import APIRouter, Depends

from app.schemas.admin_platform import (
    PlatformConfigOut,
    PlatformConfigUpdateRequest,
    FeatureFlagsOut,
    FeatureFlagsUpdateRequest,
    LicensesOut,
    BrandingOut,
    BrandingUpdateRequest,
)
from app.models.user import platform_config_db, feature_flags_db, licenses_db, branding_db
from app.core.security import get_current_admin

router = APIRouter(prefix="/api/v1/admin", tags=["Admin: Platform Configuration"])


@router.get("/config", response_model=PlatformConfigOut)
def get_config(current_admin: dict = Depends(get_current_admin)):
    return platform_config_db


@router.patch("/config", response_model=PlatformConfigOut)
def update_config(
    data: PlatformConfigUpdateRequest,
    current_admin: dict = Depends(get_current_admin),
):
    updates = data.model_dump(exclude_unset=True)
    platform_config_db.update(updates)
    return platform_config_db


@router.get("/features", response_model=FeatureFlagsOut)
def get_features(current_admin: dict = Depends(get_current_admin)):
    return feature_flags_db


@router.patch("/features", response_model=FeatureFlagsOut)
def update_features(
    data: FeatureFlagsUpdateRequest,
    current_admin: dict = Depends(get_current_admin),
):
    updates = data.model_dump(exclude_unset=True)
    feature_flags_db.update(updates)
    return feature_flags_db


@router.get("/licenses", response_model=LicensesOut)
def get_licenses(current_admin: dict = Depends(get_current_admin)):
    return licenses_db


@router.patch("/branding", response_model=BrandingOut)
def update_branding(
    data: BrandingUpdateRequest,
    current_admin: dict = Depends(get_current_admin),
):
    updates = data.model_dump(exclude_unset=True)
    branding_db.update(updates)
    return branding_db