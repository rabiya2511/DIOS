"""
Pydantic schemas for the Preferences domain (Notifications APIs
blueprint) — notification channel toggles and topic subscriptions.
Distinct from the general /me/preferences free-form dict.
"""

from datetime import datetime

from pydantic import BaseModel


class NotificationPreferencesResponse(BaseModel):
    email_enabled: bool
    sms_enabled: bool
    push_enabled: bool
    inapp_enabled: bool


class NotificationPreferencesUpdateRequest(BaseModel):
    email_enabled: bool | None = None
    sms_enabled: bool | None = None
    push_enabled: bool | None = None
    inapp_enabled: bool | None = None


class SubscriptionCreateRequest(BaseModel):
    topic: str


class SubscriptionResponse(BaseModel):
    topic: str
    subscribed_at: datetime