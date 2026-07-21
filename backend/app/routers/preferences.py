"""
Notification Preferences router — channel toggles + topic subscriptions.
Matches the Preferences section of the Notifications APIs blueprint (4/4).
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.schemas.notification_preferences import (
    NotificationPreferencesResponse,
    NotificationPreferencesUpdateRequest,
    SubscriptionCreateRequest,
    SubscriptionResponse,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1", tags=["Notification Preferences"])

# email -> {email_enabled, sms_enabled, push_enabled, inapp_enabled}
notification_preferences_db: dict[str, dict] = {}

# email -> list of {topic, subscribed_at}
subscriptions_db: dict[str, list] = {}


def _get_or_create_prefs(email: str) -> dict:
    return notification_preferences_db.setdefault(
        email,
        {"email_enabled": True, "sms_enabled": True, "push_enabled": True, "inapp_enabled": True},
    )


@router.get("/notification-preferences", response_model=NotificationPreferencesResponse)
def get_preferences(current_user: dict = Depends(get_current_user)):
    return _get_or_create_prefs(current_user["email"])


@router.patch("/notification-preferences", response_model=NotificationPreferencesResponse)
def update_preferences(
    data: NotificationPreferencesUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    prefs = _get_or_create_prefs(current_user["email"])
    for field in ("email_enabled", "sms_enabled", "push_enabled", "inapp_enabled"):
        value = getattr(data, field)
        if value is not None:
            prefs[field] = value
    return prefs


@router.get("/subscriptions", response_model=list[SubscriptionResponse])
def get_subscriptions(current_user: dict = Depends(get_current_user)):
    return subscriptions_db.get(current_user["email"], [])


@router.post("/subscriptions", response_model=SubscriptionResponse, status_code=201)
def subscribe(
    data: SubscriptionCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    subs = subscriptions_db.setdefault(current_user["email"], [])
    existing = next((s for s in subs if s["topic"] == data.topic), None)
    if existing:
        return existing

    entry = {"topic": data.topic, "subscribed_at": datetime.now(timezone.utc)}
    subs.append(entry)
    return entry