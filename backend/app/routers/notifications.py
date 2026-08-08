"""
Notification Management router — list, get, create, update, delete.

Authentication is enabled.

GET/PATCH/DELETE are restricted to notifications belonging
to the currently authenticated user.

POST requires an authenticated user and allows the authenticated
user to create a notification for a recipient.
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


router = APIRouter(
    prefix="/api/v1/notification-items",
    tags=["Notifications"],
)


# ---------------------------------------------------------
# In-memory notification database
# ---------------------------------------------------------

notifications_db: dict[str, dict] = {}


# ---------------------------------------------------------
# Get notification belonging to current user
# ---------------------------------------------------------

def get_own_notification_or_404(
    notification_id: str,
    email: str,
) -> dict:

    notification = notifications_db.get(notification_id)

    if notification is None:
        raise HTTPException(
            status_code=404,
            detail="Notification not found",
        )

    if notification["recipient_email"] != email:
        raise HTTPException(
            status_code=404,
            detail="Notification not found",
        )

    return notification


# ---------------------------------------------------------
# LIST NOTIFICATIONS
# ---------------------------------------------------------

@router.get(
    "",
    response_model=list[NotificationResponse],
)
def list_notifications(
    current_user: dict = Depends(get_current_user),
):
    """
    Return notifications belonging to the logged-in user.
    """

    return [
        notification
        for notification in notifications_db.values()
        if notification["recipient_email"] == current_user["email"]
    ]


# ---------------------------------------------------------
# GET SINGLE NOTIFICATION
# ---------------------------------------------------------

@router.get(
    "/{id}",
    response_model=NotificationResponse,
)
def get_notification(
    id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Get one notification belonging to the logged-in user.
    """

    return get_own_notification_or_404(
        id,
        current_user["email"],
    )


# ---------------------------------------------------------
# CREATE NOTIFICATION
# ---------------------------------------------------------

@router.post(
    "",
    response_model=NotificationResponse,
    status_code=201,
)
def create_notification(
    data: NotificationCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Create a notification.

    The request must be authenticated.
    """

    notification_id = str(uuid4())

    now = datetime.now(timezone.utc)

    notification = {
        "id": notification_id,
        "recipient_email": data.recipient_email,
        "title": data.title,
        "body": data.body,
        "type": data.type,
        "read": False,
        "created_at": now,
    }

    notifications_db[notification_id] = notification

    return notification


# ---------------------------------------------------------
# UPDATE NOTIFICATION
# ---------------------------------------------------------

@router.patch(
    "/{id}",
    response_model=NotificationResponse,
)
def update_notification(
    id: str,
    data: NotificationUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Update a notification belonging to the logged-in user.
    """

    notification = get_own_notification_or_404(
        id,
        current_user["email"],
    )

    if data.title is not None:
        notification["title"] = data.title

    if data.body is not None:
        notification["body"] = data.body

    if data.read is not None:
        notification["read"] = data.read

    return notification


# ---------------------------------------------------------
# DELETE NOTIFICATION
# ---------------------------------------------------------

@router.delete(
    "/{id}",
    status_code=204,
)
def delete_notification(
    id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Delete a notification belonging to the logged-in user.
    """

    get_own_notification_or_404(
        id,
        current_user["email"],
    )

    del notifications_db[id]

    return None