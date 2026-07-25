"""
Alerts router — create, list, update status/severity, view history.
Matches the Alerts section of the Analytics APIs blueprint (4/4).
Only the alert owner can update it.

Literal-path route (/history) MUST come before the dynamic /{id}
route below — same ordering rule used throughout this codebase.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.alerts import (
    AlertCreateRequest,
    AlertUpdateRequest,
    AlertResponse,
    AlertHistoryEntry,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/alerts", tags=["Alerts"])

VALID_SEVERITIES = {"info", "warning", "critical"}
VALID_STATUSES = {"active", "acknowledged", "resolved"}

# id -> {id, name, condition, severity, status, owner_email, created_at, updated_at}
alerts_db: dict[str, dict] = {}

# append-only history log
alert_history_db: list[dict] = []


def _get_alert_or_404(id: str) -> dict:
    alert = alerts_db.get(id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


def _require_owner(alert: dict, email: str):
    if alert["owner_email"] != email:
        raise HTTPException(status_code=403, detail="Only the alert owner can perform this action")


def _log_history(alert_id: str, action: str, detail: str, actor_email: str):
    alert_history_db.append(
        {
            "alert_id": alert_id,
            "action": action,
            "detail": detail,
            "actor_email": actor_email,
            "timestamp": datetime.now(timezone.utc),
        }
    )


@router.post("", response_model=AlertResponse, status_code=201)
def create_alert(
    data: AlertCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    if data.severity not in VALID_SEVERITIES:
        raise HTTPException(
            status_code=422, detail=f"severity must be one of {sorted(VALID_SEVERITIES)}"
        )
    alert_id = str(uuid4())
    now = datetime.now(timezone.utc)
    alerts_db[alert_id] = {
        "id": alert_id,
        "name": data.name,
        "condition": data.condition,
        "severity": data.severity,
        "status": "active",
        "owner_email": current_user["email"],
        "created_at": now,
        "updated_at": now,
    }
    _log_history(alert_id, "created", f"severity={data.severity}", current_user["email"])
    return alerts_db[alert_id]


@router.get("", response_model=list[AlertResponse])
def list_alerts(current_user: dict = Depends(get_current_user)):
    return [a for a in alerts_db.values() if a["owner_email"] == current_user["email"]]


# ─── Literal-path routes MUST come before any /{id} routes below ───

@router.get("/history", response_model=list[AlertHistoryEntry])
def get_alert_history(current_user: dict = Depends(get_current_user)):
    owned_ids = {a["id"] for a in alerts_db.values() if a["owner_email"] == current_user["email"]}
    return [entry for entry in alert_history_db if entry["alert_id"] in owned_ids]


# ─── Dynamic /{id} routes come LAST ───

@router.patch("/{id}", response_model=AlertResponse)
def update_alert(
    id: str,
    data: AlertUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    alert = _get_alert_or_404(id)
    _require_owner(alert, current_user["email"])

    if data.status is not None:
        if data.status not in VALID_STATUSES:
            raise HTTPException(
                status_code=422, detail=f"status must be one of {sorted(VALID_STATUSES)}"
            )
        alert["status"] = data.status
        _log_history(id, "status_changed", data.status, current_user["email"])

    if data.severity is not None:
        if data.severity not in VALID_SEVERITIES:
            raise HTTPException(
                status_code=422, detail=f"severity must be one of {sorted(VALID_SEVERITIES)}"
            )
        alert["severity"] = data.severity
        _log_history(id, "severity_changed", data.severity, current_user["email"])

    alert["updated_at"] = datetime.now(timezone.utc)
    return alert