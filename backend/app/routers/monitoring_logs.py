"""
Logs router — list, search, get, export.
Matches the Logs section of the Monitoring APIs blueprint (4/4).
Seeded with sample entries since there's no real logging pipeline.
"""

import csv
import io
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas.monitoring_logs import LogEntryResponse, LogSearchRequest

router = APIRouter(prefix="/api/v1/logs", tags=["Monitoring Logs"])

# id -> {id, level, message, source, timestamp}
logs_db: dict[str, dict] = {}


def _seed_logs():
    if logs_db:
        return
    now = datetime.now(timezone.utc)
    samples = [
        ("info", "Application startup complete", "app.main"),
        ("info", "Database connection pool initialized", "app.db"),
        ("warning", "Slow query detected (450ms)", "app.db"),
        ("error", "Failed to connect to email provider", "app.routers.email"),
        ("info", "Scheduled backup completed", "app.routers.admin_backup"),
        ("warning", "Rate limit threshold approaching for IP 203.0.113.4", "app.middleware"),
    ]
    for i, (level, message, source) in enumerate(samples):
        log_id = str(uuid4())
        logs_db[log_id] = {
            "id": log_id,
            "level": level,
            "message": message,
            "source": source,
            "timestamp": now - timedelta(minutes=(len(samples) - i) * 5),
        }


_seed_logs()


@router.get("", response_model=list[LogEntryResponse])
def list_logs():
    return sorted(logs_db.values(), key=lambda l: l["timestamp"], reverse=True)


@router.post("/search", response_model=list[LogEntryResponse])
def search_logs(data: LogSearchRequest):
    results = list(logs_db.values())
    if data.level:
        results = [l for l in results if l["level"] == data.level]
    if data.query:
        q = data.query.lower()
        results = [l for l in results if q in l["message"].lower()]
    return sorted(results, key=lambda l: l["timestamp"], reverse=True)


@router.get("/{id}", response_model=LogEntryResponse)
def get_log(id: str):
    log = logs_db.get(id)
    if not log:
        raise HTTPException(status_code=404, detail="Log entry not found")
    return log


@router.post("/export")
def export_logs():
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=["id", "level", "message", "source", "timestamp"])
    writer.writeheader()
    for log in sorted(logs_db.values(), key=lambda l: l["timestamp"], reverse=True):
        writer.writerow(
            {
                "id": log["id"],
                "level": log["level"],
                "message": log["message"],
                "source": log["source"],
                "timestamp": log["timestamp"].isoformat(),
            }
        )
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=logs_export.csv"},
    )