"""
Administration router — metrics, health, logs, config.
Matches the Administration section of the Notifications APIs
blueprint (4/4). Aggregates data across Email, SMS & Push, In-App,
and Notification Management (notification-items).
"""

from fastapi import APIRouter, Depends

from app.schemas.notifications_admin import (
    NotificationsMetricsResponse,
    NotificationsHealthResponse,
    NotificationsLogEntry,
    NotificationsConfigResponse,
    NotificationsConfigUpdateRequest,
)
from app.routers.email import email_history_db
from app.routers.sms_push import sms_history_db, push_history_db
from app.routers.inapp import inapp_messages_db
from app.routers.notifications import notifications_db
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/notifications", tags=["Notifications Administration"])

_config = {
    "rate_limit_per_minute": 60,
    "retry_attempts": 3,
    "default_channel": "email",
}


@router.get("/metrics", response_model=NotificationsMetricsResponse)
def get_metrics():
    return NotificationsMetricsResponse(
        emails_sent=len(email_history_db),
        sms_sent=len(sms_history_db),
        push_sent=len(push_history_db),
        inapp_sent=len(inapp_messages_db),
        notification_items_created=len(notifications_db),
    )


@router.get("/health", response_model=NotificationsHealthResponse)
def get_health():
    # STUB: real version would ping each provider (SendGrid, Twilio, FCM, etc.)
    return NotificationsHealthResponse(
        status="ok",
        channels={"email": "ok", "sms": "ok", "push": "ok", "inapp": "ok"},
    )


@router.get("/logs", response_model=list[NotificationsLogEntry])
def get_logs():
    entries = []
    for e in email_history_db:
        entries.append({"channel": "email", "detail": f"sent to {e['to_email']}", "timestamp": e["sent_at"]})
    for s in sms_history_db:
        entries.append({"channel": "sms", "detail": f"sent to {s['to_phone']}", "timestamp": s["sent_at"]})
    for p in push_history_db:
        entries.append({"channel": "push", "detail": f"sent to {p['to_email']}", "timestamp": p["sent_at"]})
    entries.sort(key=lambda e: e["timestamp"])
    return entries


@router.patch("/config", response_model=NotificationsConfigResponse)
def update_config(
    data: NotificationsConfigUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    if data.rate_limit_per_minute is not None:
        _config["rate_limit_per_minute"] = data.rate_limit_per_minute
    if data.retry_attempts is not None:
        _config["retry_attempts"] = data.retry_attempts
    if data.default_channel is not None:
        _config["default_channel"] = data.default_channel
    return _config