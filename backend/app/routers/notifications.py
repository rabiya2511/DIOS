"""
Notification Management router — list, get, create, update, delete.
Matches the Notification Management section of the Notifications APIs
blueprint (5/5). GET/PATCH/DELETE are scoped to the current user's own
notifications; POST allows creating a notification for any recipient
(system/admin action).

NOTE: mounted at /notification-items instead of /notifications to avoid
colliding with the existing simple GET /notifications stub in activity.py.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.notifications import (
    NotificationCreateRequest,
    NotificationUpdateRequest,
    NotificationResponse,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/notification-items", tags=["Notifications"])

# id -> {id, recipient_email, title, body, type, read, created_at}
notifications_db: dict[str, dict] = {}


def _get_own_notification_or_404(id: str, email: str) -> dict:
    n = notifications_db.get(id)
    if not n or n["recipient_email"] != email:
        raise HTTPException(status_code=404, detail="Notification not found")
    return n


@router.get("", response_model=list[NotificationResponse])
def list_notifications(current_user: dict = Depends(get_current_user)):
    return [
        n for n in notifications_db.values() if n["recipient_email"] == current_user["email"]
    ]


@router.get("/{id}", response_model=NotificationResponse)
def get_notification(id: str, current_user: dict = Depends(get_current_user)):
    return _get_own_notification_or_404(id, current_user["email"])


@router.post("", response_model=NotificationResponse, status_code=201)
def create_notification(
    data: NotificationCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    notification_id = str(uuid4())
    now = datetime.now(timezone.utc)
    notifications_db[notification_id] = {
        "id": notification_id,
        "recipient_email": data.recipient_email,
        "title": data.title,
        "body": data.body,
        "type": data.type,
        "read": False,
        "created_at": now,
    }
    return notifications_db[notification_id]


@router.patch("/{id}", response_model=NotificationResponse)
def update_notification(
    id: str,
    data: NotificationUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    n = _get_own_notification_or_404(id, current_user["email"])
    if data.title is not None:
        n["title"] = data.title
    if data.body is not None:
        n["body"] = data.body
    if data.read is not None:
        n["read"] = data.read
    return n


@router.delete("/{id}", status_code=204)
def delete_notification(id: str, current_user: dict = Depends(get_current_user)):
    _get_own_notification_or_404(id, current_user["email"])
    del notifications_db[id]
    return None