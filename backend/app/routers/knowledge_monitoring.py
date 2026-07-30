"""
Router for the Monitoring group of the Knowledge/RAG APIs blueprint.
  GET  /api/v1/knowledge/metrics
  GET  /api/v1/knowledge/usage
  GET  /api/v1/knowledge/health
  GET  /api/v1/knowledge/logs
  GET  /api/v1/knowledge/audit
  GET  /api/v1/knowledge/errors
  POST /api/v1/knowledge/cache/clear
  GET  /api/v1/knowledge/performance

*** CROSS-ROUTER COLLISION WARNING ***
This shares the /api/v1/knowledge prefix with the (separately-built,
currently broken) Knowledge Base router, which owns a dynamic
GET /api/v1/knowledge/{id} route. Every literal path in this file
(metrics, usage, health, etc.) MUST be registered in main.py BEFORE
that Knowledge Base router's include_router call, or GET /{id} will
silently swallow requests like GET /knowledge/metrics by matching
id="metrics" — the same failure mode fixed earlier for chat_sessions
vs chat_prompt_context/chat_administration/chat_reasoning_tools.

Named knowledge_monitoring.py (not monitoring.py / monitoring_admin.py
/ audit_domain.py) to avoid colliding with existing routers of similar
purpose elsewhere in the DIOS app. Uses local in-memory dicts (same
pattern as conversations_db in conversations.py).

/metrics, /usage, and /performance return placeholder values — this
module has no access to the real document/chunk/embedding stores that
will live in future Documents/Chunking/Embeddings routers. Wire these
up to real aggregate queries once those modules exist.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.schemas.knowledge_monitoring import (
    KnowledgeMetricsResponse,
    KnowledgeUsageResponse,
    KnowledgeHealthResponse,
    KnowledgeLogsResponse,
    KnowledgeAuditResponse,
    KnowledgeErrorsResponse,
    KnowledgeCacheClearRequest,
    KnowledgeCacheClearResponse,
    KnowledgePerformanceResponse,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/knowledge", tags=["Knowledge/RAG Monitoring"])

_START_TIME = datetime.now(timezone.utc)

# list of {id, level, message, timestamp}
knowledge_logs_db: list[dict] = [
    {"id": str(uuid.uuid4()), "level": "INFO", "message": "Knowledge/RAG subsystem started",
     "timestamp": _START_TIME},
]
# list of {id, actor_email, action, resource_type, resource_id, detail, timestamp}
knowledge_audit_log_db: list[dict] = []
# list of {id, error_type, message, resource_id, timestamp}
knowledge_errors_db: list[dict] = []


def _record_audit(actor_email: str, action: str, resource_type: str,
                   resource_id: Optional[str] = None, detail: Optional[str] = None) -> None:
    knowledge_audit_log_db.append({
        "id": str(uuid.uuid4()),
        "actor_email": actor_email,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "detail": detail,
        "timestamp": datetime.now(timezone.utc),
    })


# ---------------------------------------------------------------------------
# GET /api/v1/knowledge/metrics
# ---------------------------------------------------------------------------
@router.get("/metrics", response_model=KnowledgeMetricsResponse)
def get_knowledge_metrics(current_user: dict = Depends(get_current_user)):
    """Aggregate knowledge base metrics. Placeholder values — see module docstring."""
    return KnowledgeMetricsResponse(
        total_documents=0, total_chunks=0, total_embeddings=0,
        avg_query_latency_ms=0.0, generated_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# GET /api/v1/knowledge/usage
# ---------------------------------------------------------------------------
@router.get("/usage", response_model=KnowledgeUsageResponse)
def get_knowledge_usage(
    period_start: Optional[datetime] = Query(None),
    period_end: Optional[datetime] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    """RAG query/embedding usage stats. Placeholder values — see module docstring."""
    return KnowledgeUsageResponse(
        total_queries=0, total_tokens_embedded=0,
        period_start=period_start, period_end=period_end,
        generated_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# GET /api/v1/knowledge/health
# ---------------------------------------------------------------------------
@router.get("/health", response_model=KnowledgeHealthResponse)
def get_knowledge_health(current_user: dict = Depends(get_current_user)):
    """Health check for the knowledge/RAG subsystem."""
    now = datetime.now(timezone.utc)
    uptime = (now - _START_TIME).total_seconds()
    return KnowledgeHealthResponse(status="ok", uptime_seconds=uptime, checked_at=now)


# ---------------------------------------------------------------------------
# GET /api/v1/knowledge/logs
# ---------------------------------------------------------------------------
@router.get("/logs", response_model=KnowledgeLogsResponse)
def get_knowledge_logs(
    level: Optional[str] = Query(None, description="Filter by log level"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    """Retrieve knowledge/RAG subsystem logs."""
    entries = knowledge_logs_db
    if level:
        entries = [e for e in entries if e["level"] == level.upper()]

    entries_sorted = sorted(entries, key=lambda e: e["timestamp"], reverse=True)
    total = len(entries_sorted)
    page = entries_sorted[offset: offset + limit]
    return KnowledgeLogsResponse(total=total, items=page)


# ---------------------------------------------------------------------------
# GET /api/v1/knowledge/audit
# ---------------------------------------------------------------------------
@router.get("/audit", response_model=KnowledgeAuditResponse)
def get_knowledge_audit(
    action: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    """Retrieve the audit log of admin actions taken through this module."""
    entries = knowledge_audit_log_db
    if action:
        entries = [e for e in entries if e["action"] == action]

    entries_sorted = sorted(entries, key=lambda e: e["timestamp"], reverse=True)
    total = len(entries_sorted)
    page = entries_sorted[offset: offset + limit]
    return KnowledgeAuditResponse(total=total, items=page)


# ---------------------------------------------------------------------------
# GET /api/v1/knowledge/errors
# ---------------------------------------------------------------------------
@router.get("/errors", response_model=KnowledgeErrorsResponse)
def get_knowledge_errors(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    """Retrieve recent errors from the knowledge/RAG subsystem."""
    entries_sorted = sorted(knowledge_errors_db, key=lambda e: e["timestamp"], reverse=True)
    total = len(entries_sorted)
    page = entries_sorted[offset: offset + limit]
    return KnowledgeErrorsResponse(total=total, items=page)


# ---------------------------------------------------------------------------
# POST /api/v1/knowledge/cache/clear
# ---------------------------------------------------------------------------
@router.post("/cache/clear", response_model=KnowledgeCacheClearResponse)
def clear_knowledge_cache(
    payload: KnowledgeCacheClearRequest,
    current_user: dict = Depends(get_current_user),
):
    """Clear knowledge/RAG caches (embeddings, vector index, or all)."""
    now = datetime.now(timezone.utc)
    _record_audit(
        current_user.get("email", "unknown"), "cache_cleared", "knowledge_cache",
        detail=f"scope={payload.scope}",
    )
    return KnowledgeCacheClearResponse(scope=payload.scope, cleared=True, cleared_at=now)


# ---------------------------------------------------------------------------
# GET /api/v1/knowledge/performance
# ---------------------------------------------------------------------------
@router.get("/performance", response_model=KnowledgePerformanceResponse)
def get_knowledge_performance(current_user: dict = Depends(get_current_user)):
    """RAG pipeline performance stats. Placeholder values — see module docstring."""
    return KnowledgePerformanceResponse(
        avg_query_latency_ms=0.0, p95_latency_ms=0.0, avg_indexing_time_ms=0.0,
        generated_at=datetime.now(timezone.utc),
    )