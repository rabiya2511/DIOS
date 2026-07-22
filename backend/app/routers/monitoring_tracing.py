"""
Tracing router — traces, single trace, spans, trace search.
Matches the Tracing section of the Monitoring APIs blueprint (4/4).
Seeded with sample distributed-tracing data.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from app.schemas.monitoring_tracing import TraceResponse, SpanResponse, TraceSearchRequest

router = APIRouter(prefix="/api/v1", tags=["Monitoring Tracing"])

# id -> {id, name, status, duration_ms, started_at}
traces_db: dict[str, dict] = {}

# id -> {id, trace_id, name, duration_ms, started_at}
spans_db: dict[str, dict] = {}


def _seed_traces():
    if traces_db:
        return
    now = datetime.now(timezone.utc)

    trace_specs = [
        ("POST /api/v1/auth/login", "ok", 42.5, [
            ("verify_password", 12.1), ("create_access_token", 3.4), ("create_refresh_token", 2.8),
        ]),
        ("GET /api/v1/organizations/{id}/members", "ok", 18.9, [
            ("db_lookup_org", 8.2), ("db_lookup_members", 9.1),
        ]),
        ("POST /api/v1/email/send", "error", 305.7, [
            ("resolve_template", 4.0), ("provider_call", 298.2),
        ]),
    ]

    for i, (name, status, duration, spans) in enumerate(trace_specs):
        trace_id = str(uuid4())
        started_at = now - timedelta(minutes=(len(trace_specs) - i) * 3)
        traces_db[trace_id] = {
            "id": trace_id,
            "name": name,
            "status": status,
            "duration_ms": duration,
            "started_at": started_at,
        }
        for span_name, span_duration in spans:
            span_id = str(uuid4())
            spans_db[span_id] = {
                "id": span_id,
                "trace_id": trace_id,
                "name": span_name,
                "duration_ms": span_duration,
                "started_at": started_at,
            }


_seed_traces()


@router.get("/traces", response_model=list[TraceResponse])
def list_traces():
    return sorted(traces_db.values(), key=lambda t: t["started_at"], reverse=True)


@router.get("/traces/{id}", response_model=TraceResponse)
def get_trace(id: str):
    trace = traces_db.get(id)
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    return trace


@router.get("/spans", response_model=list[SpanResponse])
def list_spans(trace_id: str | None = None):
    spans = list(spans_db.values())
    if trace_id:
        spans = [s for s in spans if s["trace_id"] == trace_id]
    return sorted(spans, key=lambda s: s["started_at"])


@router.post("/traces/search", response_model=list[TraceResponse])
def search_traces(data: TraceSearchRequest):
    results = list(traces_db.values())
    if data.status:
        results = [t for t in results if t["status"] == data.status]
    if data.query:
        q = data.query.lower()
        results = [t for t in results if q in t["name"].lower()]
    return sorted(results, key=lambda t: t["started_at"], reverse=True)