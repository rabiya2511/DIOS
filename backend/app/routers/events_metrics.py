"""
Events & Metrics router — event logging, system/business/realtime metrics.
Matches the Events & Metrics section of the Analytics APIs blueprint (5/5).

System/business/realtime metrics are mock/derived values — this
environment has no real infrastructure to sample CPU/memory/traffic
from, so these return plausible placeholder numbers plus real counts
where data is available (event log size, conversation count).
"""

import random
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends

from app.schemas.events_metrics import (
    EventCreateRequest,
    EventResponse,
    SystemMetricsResponse,
    BusinessMetricsResponse,
    RealtimeMetricsResponse,
)
from app.core.security import get_current_user
from app.routers.conversations import conversations_db

router = APIRouter(prefix="/api/v1", tags=["Events & Metrics"])

# id -> {id, name, payload, actor_email, timestamp}
events_db: dict[str, dict] = {}

_SERVER_STARTED_AT = datetime.now(timezone.utc)


@router.post("/events", response_model=EventResponse, status_code=201)
def create_event(
    data: EventCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    event_id = str(uuid4())
    now = datetime.now(timezone.utc)
    events_db[event_id] = {
        "id": event_id,
        "name": data.name,
        "payload": data.payload,
        "actor_email": current_user["email"],
        "timestamp": now,
    }
    return events_db[event_id]


@router.get("/events", response_model=list[EventResponse])
def list_events(current_user: dict = Depends(get_current_user)):
    return [e for e in events_db.values() if e["actor_email"] == current_user["email"]]


@router.get("/metrics/system", response_model=SystemMetricsResponse)
def get_system_metrics(current_user: dict = Depends(get_current_user)):
    uptime = int((datetime.now(timezone.utc) - _SERVER_STARTED_AT).total_seconds())
    return SystemMetricsResponse(
        cpu_usage_percent=round(random.uniform(5, 60), 2),
        memory_usage_percent=round(random.uniform(20, 80), 2),
        disk_usage_percent=round(random.uniform(10, 70), 2),
        uptime_seconds=uptime,
        generated_at=datetime.now(timezone.utc),
    )


@router.get("/metrics/business", response_model=BusinessMetricsResponse)
def get_business_metrics(current_user: dict = Depends(get_current_user)):
    active_users = len({e["actor_email"] for e in events_db.values()})
    return BusinessMetricsResponse(
        active_users=active_users,
        total_events_logged=len(events_db),
        total_conversations=len(conversations_db),
        generated_at=datetime.now(timezone.utc),
    )


@router.get("/metrics/realtime", response_model=RealtimeMetricsResponse)
def get_realtime_metrics(current_user: dict = Depends(get_current_user)):
    return RealtimeMetricsResponse(
        requests_per_second=round(random.uniform(1, 50), 2),
        active_connections=random.randint(1, 20),
        error_rate_percent=round(random.uniform(0, 5), 2),
        generated_at=datetime.now(timezone.utc),
    )