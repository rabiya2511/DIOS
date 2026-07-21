"""
Alerts router — create, list, update, history.
Matches the Alerts section of the Monitoring APIs blueprint (4/4).
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.monitoring_alerts import (
    AlertCreateRequest,
    AlertUpdateRequest,
    AlertResponse,
    AlertHistoryEntry,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/alerts", tags=["Monitoring Alerts"])

# id -> {id, title, description, severity, status, created_at, updated_at}
alerts_db: dict[str, dict] = {}

# append-only status-change log
alert_history_db: list[dict] = []


def _log_status_change(alert_id: str, status: str):
    alert_history_db.append(
        {"alert_id": alert_id, "status": status, "timestamp": datetime.now(timezone.utc)}
    )


@router.post("", response_model=AlertResponse, status_code=201)
def create_alert(
    data: AlertCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    alert_id = str(uuid4())
    now = datetime.now(timezone.utc)
    alerts_db[alert_id] = {
        "id": alert_id,
        "title": data.title,
        "description": data.description,
        "severity": data.severity,
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }
    _log_status_change(alert_id, "active")
    return alerts_db[alert_id]


@router.get("", response_model=list[AlertResponse])
def list_alerts():
    return list(alerts_db.values())


@router.get("/history", response_model=list[AlertHistoryEntry])
def get_alert_history():
    return list(alert_history_db)


@router.patch("/{id}", response_model=AlertResponse)
def update_alert(
    id: str,
    data: AlertUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    alert = alerts_db.get(id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    if data.title is not None:
        alert["title"] = data.title
    if data.description is not None:
        alert["description"] = data.description
    if data.status is not None and data.status != alert["status"]:
        alert["status"] = data.status
        _log_status_change(id, data.status)

    alert["updated_at"] = datetime.now(timezone.utc)
    return alert