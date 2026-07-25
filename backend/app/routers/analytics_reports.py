"""
Analytics router — Reports.
Matches the Reports section of the Analytics APIs blueprint (5/5).
"""

import csv
import io
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas.analytics_reports import (
    ReportCreateRequest,
    ReportOut,
    ReportGenerateRequest,
    ReportRunOut,
    ReportScheduleRequest,
    ReportExportRequest,
)
from app.models.user import reports_db, report_runs_db, users_db, audit_logs_db
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/reports", tags=["Analytics: Reports"])


def _get_owned_report(report_id: str, current_user: dict) -> dict:
    report = reports_db.get(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if report["owner_email"] != current_user["email"]:
        raise HTTPException(status_code=403, detail="Only the report owner can perform this action")
    return report


@router.post("", response_model=ReportOut, status_code=201)
def create_report(
    data: ReportCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    report_id = str(uuid4())
    report = {
        "id": report_id,
        "name": data.name,
        "type": data.type,
        "filters": data.filters,
        "owner_email": current_user["email"],
        "schedule": None,
        "created_at": datetime.now(timezone.utc),
    }
    reports_db[report_id] = report
    return report


@router.get("", response_model=list[ReportOut])
def list_reports(current_user: dict = Depends(get_current_user)):
    email = current_user["email"]
    return [r for r in reports_db.values() if r["owner_email"] == email]


@router.post("/generate", response_model=ReportRunOut, status_code=201)
def generate_report(
    data: ReportGenerateRequest,
    current_user: dict = Depends(get_current_user),
):
    report = _get_owned_report(data.report_id, current_user)
    # STUB: simulated result based on existing stats, real version would
    # query per report["type"]/report["filters"].
    result = {
        "type": report["type"],
        "total_users": len(users_db),
        "total_audit_events": len(audit_logs_db),
    }
    run = {
        "id": str(uuid4()),
        "report_id": data.report_id,
        "result": result,
        "generated_at": datetime.now(timezone.utc),
    }
    report_runs_db.setdefault(data.report_id, []).append(run)
    return run


@router.post("/export")
def export_report(
    data: ReportExportRequest,
    current_user: dict = Depends(get_current_user),
):
    report = _get_owned_report(data.report_id, current_user)
    runs = report_runs_db.get(data.report_id, [])

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=["run_id", "generated_at", "result"])
    writer.writeheader()
    for run in runs:
        writer.writerow({
            "run_id": run["id"],
            "generated_at": run["generated_at"].isoformat(),
            "result": str(run["result"]),
        })
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=report_{report['id']}_export.csv"},
    )


@router.post("/schedule", response_model=ReportOut)
def schedule_report(
    data: ReportScheduleRequest,
    current_user: dict = Depends(get_current_user),
):
    report = _get_owned_report(data.report_id, current_user)
    report["schedule"] = data.schedule
    return report