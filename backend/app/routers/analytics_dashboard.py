"""
Analytics router — Dashboards.
Matches the Dashboards section of the Analytics APIs blueprint (5/5).
"""

import csv
import io
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas.analytics_dashboard import (
    WidgetCreateRequest,
    WidgetUpdateRequest,
    WidgetOut,
    DashboardOut,
    OverviewOut,
)
from app.models.user import dashboard_widgets_db, users_db, organizations_db
from app.routers.projects import projects_db
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics: Dashboards"])


@router.get("/dashboard", response_model=DashboardOut)
def get_dashboard(current_user: dict = Depends(get_current_user)):
    email = current_user["email"]
    widgets = [w for w in dashboard_widgets_db.values() if w["owner_email"] == email]
    return DashboardOut(owner_email=email, widgets=widgets)


@router.get("/overview", response_model=OverviewOut)
def get_overview(current_user: dict = Depends(get_current_user)):
    return OverviewOut(
        total_users=len(users_db),
        total_projects=len(projects_db),
        total_organizations=len(organizations_db),
    )


@router.post("/widgets", response_model=WidgetOut, status_code=201)
def create_widget(
    data: WidgetCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    widget_id = str(uuid4())
    widget = {
        "id": widget_id,
        "owner_email": current_user["email"],
        "title": data.title,
        "type": data.type,
        "config": data.config,
        "created_at": datetime.now(timezone.utc),
    }
    dashboard_widgets_db[widget_id] = widget
    return widget


@router.patch("/widgets/{widget_id}", response_model=WidgetOut)
def update_widget(
    widget_id: str,
    data: WidgetUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    widget = dashboard_widgets_db.get(widget_id)
    if not widget:
        raise HTTPException(status_code=404, detail="Widget not found")
    if widget["owner_email"] != current_user["email"]:
        raise HTTPException(status_code=403, detail="Only the widget owner can perform this action")

    if data.title is not None:
        widget["title"] = data.title
    if data.config is not None:
        widget["config"] = data.config
    return widget


@router.get("/export")
def export_dashboard(current_user: dict = Depends(get_current_user)):
    email = current_user["email"]
    widgets = [w for w in dashboard_widgets_db.values() if w["owner_email"] == email]

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=["id", "title", "type", "created_at"])
    writer.writeheader()
    for w in widgets:
        writer.writerow({
            "id": w["id"],
            "title": w["title"],
            "type": w["type"],
            "created_at": w["created_at"].isoformat(),
        })
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=dashboard_export.csv"},
    )