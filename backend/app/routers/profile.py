"""
Profile router — GET/PATCH /me, avatar upload/delete, preferences,
language, timezone, display_name, bio.
Matches the Profile section of the User Management blueprint (8/8).
STUBBED: avatar upload doesn't hit real storage; returns a fake URL.
Defaults (avatar_url=None, preferences={}, language="en", timezone="UTC",
display_name=None, bio=None) are applied on read/write here rather than
requiring a users_db migration, so it works against existing user
records created before this router existed.
"""

from fastapi import APIRouter, Depends

from app.schemas.profile import (
    ProfileResponse,
    ProfileUpdateRequest,
    AvatarUploadRequest,
    AvatarResponse,
    PreferencesResponse,
    PreferencesUpdateRequest,
    LanguageUpdateRequest,
    TimezoneUpdateRequest,
    DisplayNameUpdateRequest,
    BioUpdateRequest,
    ThemeUpdateRequest,
    NotificationsPreferencesUpdateRequest,
    PrivacyPreferencesUpdateRequest,
    AccessibilityPreferencesUpdateRequest,
    AIPreferencesUpdateRequest,
    EmailPreferencesUpdateRequest,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/me", tags=["Profile"])


def _profile_defaults(user: dict) -> dict:
    user.setdefault("avatar_url", None)
    user.setdefault("preferences", {})
    user.setdefault("language", "en")
    user.setdefault("timezone", "UTC")
    user.setdefault("display_name", None)
    user.setdefault("bio", None)
    return user


@router.get("", response_model=ProfileResponse)
def get_profile(current_user: dict = Depends(get_current_user)):
    return ProfileResponse(**_profile_defaults(current_user))


@router.patch("", response_model=ProfileResponse)
def update_profile(
    data: ProfileUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    _profile_defaults(current_user)
    if data.full_name is not None:
        current_user["full_name"] = data.full_name
    return ProfileResponse(**current_user)


@router.post("/avatar", response_model=AvatarResponse)
def upload_avatar(
    data: AvatarUploadRequest,
    current_user: dict = Depends(get_current_user),
):
    # STUB: real version streams the file to object storage (S3, GCS, etc.)
    # and returns the real CDN URL.
    _profile_defaults(current_user)
    fake_url = f"https://cdn.example.com/avatars/{current_user['id']}/{data.filename}"
    current_user["avatar_url"] = fake_url
    return AvatarResponse(avatar_url=fake_url)


@router.delete("/avatar", status_code=204)
def delete_avatar(current_user: dict = Depends(get_current_user)):
    _profile_defaults(current_user)
    current_user["avatar_url"] = None
    return None


@router.get("/preferences", response_model=PreferencesResponse)
def get_preferences(current_user: dict = Depends(get_current_user)):
    _profile_defaults(current_user)
    return PreferencesResponse(preferences=current_user["preferences"])


@router.patch("/preferences", response_model=PreferencesResponse)
def update_preferences(
    data: PreferencesUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    _profile_defaults(current_user)
    current_user["preferences"].update(data.preferences)
    return PreferencesResponse(preferences=current_user["preferences"])


@router.patch("/language", response_model=ProfileResponse)
def update_language(
    data: LanguageUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    _profile_defaults(current_user)
    current_user["language"] = data.language
    return ProfileResponse(**current_user)


@router.patch("/timezone", response_model=ProfileResponse)
def update_timezone(
    data: TimezoneUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    _profile_defaults(current_user)
    current_user["timezone"] = data.timezone
    return ProfileResponse(**current_user)


@router.patch("/display-name", response_model=ProfileResponse)
def update_display_name(
    data: DisplayNameUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    _profile_defaults(current_user)
    current_user["display_name"] = data.display_name
    return ProfileResponse(**current_user)


@router.patch("/bio", response_model=ProfileResponse)
def update_bio(
    data: BioUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    _profile_defaults(current_user)
    current_user["bio"] = data.bio
    return ProfileResponse(**current_user) 
@router.patch("/preferences/theme", response_model=PreferencesResponse)
def update_theme_preference(
    data: ThemeUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    _profile_defaults(current_user)
    current_user["preferences"]["theme"] = data.theme
    return PreferencesResponse(preferences=current_user["preferences"])


@router.patch("/preferences/notifications", response_model=PreferencesResponse)
def update_notifications_preference(
    data: NotificationsPreferencesUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    _profile_defaults(current_user)
    current_user["preferences"]["notifications"] = data.notifications
    return PreferencesResponse(preferences=current_user["preferences"])


@router.patch("/preferences/privacy", response_model=PreferencesResponse)
def update_privacy_preference(
    data: PrivacyPreferencesUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    _profile_defaults(current_user)
    current_user["preferences"]["privacy"] = data.privacy
    return PreferencesResponse(preferences=current_user["preferences"])


@router.patch("/preferences/accessibility", response_model=PreferencesResponse)
def update_accessibility_preference(
    data: AccessibilityPreferencesUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    _profile_defaults(current_user)
    current_user["preferences"]["accessibility"] = data.accessibility
    return PreferencesResponse(preferences=current_user["preferences"])


@router.patch("/preferences/ai", response_model=PreferencesResponse)
def update_ai_preference(
    data: AIPreferencesUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    _profile_defaults(current_user)
    current_user["preferences"]["ai"] = data.ai
    return PreferencesResponse(preferences=current_user["preferences"])


@router.patch("/preferences/email", response_model=PreferencesResponse)
def update_email_preference(
    data: EmailPreferencesUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    _profile_defaults(current_user)
    current_user["preferences"]["email"] = data.email
    return PreferencesResponse(preferences=current_user["preferences"]) 