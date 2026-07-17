"""
Pydantic schemas for the Profile domain (/me, avatar, preferences,
language, timezone, display_name, bio).
STUBBED: avatar upload doesn't hit real storage — it returns a fake URL.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr


class ProfileResponse(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    display_name: str | None = None
    bio: str | None = None
    avatar_url: str | None = None
    language: str
    timezone: str
    created_at: datetime


class ProfileUpdateRequest(BaseModel):
    full_name: str | None = None


class AvatarUploadRequest(BaseModel):
    # STUB: real version accepts multipart/form-data file bytes.
    # Here we accept a filename + content_type and simulate storage.
    filename: str
    content_type: str


class AvatarResponse(BaseModel):
    avatar_url: str


class PreferencesResponse(BaseModel):
    preferences: dict[str, Any]


class PreferencesUpdateRequest(BaseModel):
    preferences: dict[str, Any]


class LanguageUpdateRequest(BaseModel):
    language: str  # e.g. "en", "fr", "hi"


class TimezoneUpdateRequest(BaseModel):
    timezone: str  # e.g. "Asia/Kolkata", "UTC"


class DisplayNameUpdateRequest(BaseModel):
    display_name: str


class BioUpdateRequest(BaseModel):
    bio: str
class ThemeUpdateRequest(BaseModel):
    theme: str  # e.g. "light", "dark", "system"


class NotificationsPreferencesUpdateRequest(BaseModel):
    notifications: dict[str, Any]


class PrivacyPreferencesUpdateRequest(BaseModel):
    privacy: dict[str, Any]


class AccessibilityPreferencesUpdateRequest(BaseModel):
    accessibility: dict[str, Any]


class AIPreferencesUpdateRequest(BaseModel):
    ai: dict[str, Any]


class EmailPreferencesUpdateRequest(BaseModel):
    email: dict[str, Any]