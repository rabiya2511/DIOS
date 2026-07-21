"""
Pydantic schemas for the Administration domain (Notifications APIs
blueprint) — metrics, health, logs, config across all notification
channels built in this blueprint.
"""

from datetime import datetime

from pydantic import BaseModel


class NotificationsMetricsResponse(BaseModel):
    emails_sent: int
    sms_sent: int
    push_sent: int
    inapp_sent: int
    notification_items_created: int


class NotificationsHealthResponse(BaseModel):
    status: str
    channels: dict[str, str]


class NotificationsLogEntry(BaseModel):
    channel: str
    detail: str
    timestamp: datetime


class NotificationsConfigResponse(BaseModel):
    rate_limit_per_minute: int
    retry_attempts: int
    default_channel: str


class NotificationsConfigUpdateRequest(BaseModel):
    rate_limit_per_minute: int | None = None
    retry_attempts: int | None = None
    default_channel: str | None = None