"""
Agent Monitoring router — metrics, usage, health, logs, audit, errors,
cache clear, performance.
Matches the Monitoring section of the Agents & Planning APIs blueprint
(8/8). All read endpoints are scoped to agents the caller owns.
Named agent_monitoring.py (not monitoring.py) to avoid colliding with
the existing platform monitoring domain.

*** ROUTING WARNING ***
This router shares the /api/v1/agents prefix with agent_lifecycle.py
(GET /agents/{id}) and memory_integration.py (GET /agents/memory).
Every route below except /agents/cache/clear is a single path segment
(metrics, usage, health, logs, audit, errors, performance), so each
one collides with GET /agents/{id}. This router's app.include_router
call MUST be added to main.py BEFORE agent_lifecycle.router's call —
same requirement as memory_integration.router.

*** CROSS-ROUTER READS ***
/agents/usage and /agents/performance read tasks_db (tasks.py) and
tool_history_db (tools.py) in addition to this domain's own agents_db
import from agent_lifecycle.py, to report real cross-cutting activity
per agent rather than duplicating counters. /agents/logs, /agents/audit,
and /agents/errors are backed by dedicated stores in this file that
nothing else writes to yet — they'll return empty lists until a future
Agent Execution / Tools-error-reporting pass starts logging into them,
except for the one audit entry this router itself writes on cache clear.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends

from app.schemas.agent_monitoring import (
    AgentMetricsResponse,
    AgentUsageEntry,
    AgentUsageResponse,
    AgentHealthEntry,
    AgentHealthResponse,
    AgentLogListResponse,
    AgentAuditEntry,
    AgentAuditListResponse,
    AgentErrorListResponse,
    CacheClearResponse,
    AgentPerformanceEntry,
    AgentPerformanceResponse,
)
from app.core.security import get_current_user
from app.routers.agent_lifecycle import agents_db
from app.routers.tasks import tasks_db
from app.routers.tools import tool_history_db

router = APIRouter(prefix="/api/v1/agents", tags=["Monitoring"])

# id -> {id, agent_id, level, message, timestamp} — no writer yet, see module docstring
agent_logs_db: dict[str, dict] = {}

# id -> {id, actor_email, agent_id, action, timestamp} — written to by this router on /cache/clear
agent_audit_db: dict[str, dict] = {}

# id -> {id, agent_id, error_type, message, timestamp} — no writer yet, see module docstring
agent_errors_db: dict[str, dict] = {}

# owner_email -> {"metrics": AgentMetricsResponse, "usage": AgentUsageResponse, "performance": AgentPerformanceResponse}
# Populated lazily, cleared explicitly via POST /agents/cache/clear — no TTL.
agent_monitoring_cache_db: dict[str, dict] = {}


def _owned_agents(email: str) -> list[dict]:
    return [a for a in agents_db.values() if a["owner_email"] == email]


def _compute_metrics(email: str) -> AgentMetricsResponse:
    owned = _owned_agents(email)
    return AgentMetricsResponse(
        total_agents=len(owned),
        active_agents=sum(1 for a in owned if a["status"] == "active"),
        archived_agents=sum(1 for a in owned if a["status"] == "archived"),
        disabled_agents=sum(1 for a in owned if a["status"] == "disabled"),
        computed_at=datetime.now(timezone.utc),
    )


def _compute_usage(email: str) -> AgentUsageResponse:
    owned = _owned_agents(email)
    usage = []
    for agent in owned:
        tasks_assigned = sum(
            1 for t in tasks_db.values() if t["owner_email"] == email and t["agent_id"] == agent["id"]
        )
        tool_invocations = sum(1 for h in tool_history_db.values() if h["agent_id"] == agent["id"])
        usage.append(
            AgentUsageEntry(
                agent_id=agent["id"],
                agent_name=agent["name"],
                tasks_assigned=tasks_assigned,
                tool_invocations=tool_invocations,
            )
        )
    return AgentUsageResponse(total_agents=len(owned), usage=usage, computed_at=datetime.now(timezone.utc))


def _compute_performance(email: str) -> AgentPerformanceResponse:
    owned = _owned_agents(email)
    entries = []
    for agent in owned:
        agent_tasks = [t for t in tasks_db.values() if t["owner_email"] == email and t["agent_id"] == agent["id"]]
        tasks_completed = sum(1 for t in agent_tasks if t["status"] == "completed")
        tasks_failed = sum(1 for t in agent_tasks if t["status"] == "failed")

        agent_invocations = [h for h in tool_history_db.values() if h["agent_id"] == agent["id"]]
        inv_success = sum(1 for h in agent_invocations if h["status"] == "success")
        inv_failed = sum(1 for h in agent_invocations if h["status"] in ("failed", "unauthorized"))

        total_attempts = tasks_completed + tasks_failed + inv_success + inv_failed
        success_rate = (tasks_completed + inv_success) / total_attempts if total_attempts else 1.0

        entries.append(
            AgentPerformanceEntry(
                agent_id=agent["id"],
                agent_name=agent["name"],
                tasks_completed=tasks_completed,
                tasks_failed=tasks_failed,
                tool_invocations_success=inv_success,
                tool_invocations_failed=inv_failed,
                success_rate=round(success_rate, 2),
            )
        )
    return AgentPerformanceResponse(agents=entries, computed_at=datetime.now(timezone.utc))


@router.get("/metrics", response_model=AgentMetricsResponse)
def get_agent_metrics(current_user: dict = Depends(get_current_user)):
    email = current_user["email"]
    cached = agent_monitoring_cache_db.get(email, {}).get("metrics")
    if cached is not None:
        return cached
    result = _compute_metrics(email)
    agent_monitoring_cache_db.setdefault(email, {})["metrics"] = result
    return result


@router.get("/usage", response_model=AgentUsageResponse)
def get_agent_usage(current_user: dict = Depends(get_current_user)):
    email = current_user["email"]
    cached = agent_monitoring_cache_db.get(email, {}).get("usage")
    if cached is not None:
        return cached
    result = _compute_usage(email)
    agent_monitoring_cache_db.setdefault(email, {})["usage"] = result
    return result


@router.get("/health", response_model=AgentHealthResponse)
def get_agent_health(current_user: dict = Depends(get_current_user)):
    """Not cached — health is meant to reflect near-real-time status."""
    email = current_user["email"]
    owned = _owned_agents(email)

    entries = []
    for agent in owned:
        recent_errors = sum(1 for e in agent_errors_db.values() if e["agent_id"] == agent["id"])
        if agent["status"] != "active":
            health = "degraded"
        elif recent_errors >= 3:
            health = "unhealthy"
        elif recent_errors >= 1:
            health = "degraded"
        else:
            health = "healthy"
        entries.append(
            AgentHealthEntry(
                agent_id=agent["id"],
                agent_name=agent["name"],
                status=agent["status"],
                health=health,
                recent_error_count=recent_errors,
            )
        )

    if any(e.health == "unhealthy" for e in entries):
        overall = "unhealthy"
    elif any(e.health == "degraded" for e in entries):
        overall = "degraded"
    else:
        overall = "healthy"

    return AgentHealthResponse(overall_health=overall, agents=entries, checked_at=datetime.now(timezone.utc))


@router.get("/logs", response_model=AgentLogListResponse)
def get_agent_logs(
    agent_id: str | None = None,
    current_user: dict = Depends(get_current_user),
):
    owned_ids = {a["id"] for a in _owned_agents(current_user["email"])}
    items = [
        log for log in agent_logs_db.values()
        if log["agent_id"] in owned_ids and (agent_id is None or log["agent_id"] == agent_id)
    ]
    items.sort(key=lambda l: l["timestamp"], reverse=True)
    return AgentLogListResponse(total=len(items), items=items)


@router.get("/audit", response_model=AgentAuditListResponse)
def get_agent_audit(current_user: dict = Depends(get_current_user)):
    items = [a for a in agent_audit_db.values() if a["actor_email"] == current_user["email"]]
    items.sort(key=lambda a: a["timestamp"], reverse=True)
    return AgentAuditListResponse(total=len(items), items=items)


@router.get("/errors", response_model=AgentErrorListResponse)
def get_agent_errors(
    agent_id: str | None = None,
    current_user: dict = Depends(get_current_user),
):
    owned_ids = {a["id"] for a in _owned_agents(current_user["email"])}
    items = [
        e for e in agent_errors_db.values()
        if e["agent_id"] in owned_ids and (agent_id is None or e["agent_id"] == agent_id)
    ]
    items.sort(key=lambda e: e["timestamp"], reverse=True)
    return AgentErrorListResponse(total=len(items), items=items)


@router.post("/cache/clear", response_model=CacheClearResponse)
def clear_agent_cache(current_user: dict = Depends(get_current_user)):
    email = current_user["email"]
    agent_monitoring_cache_db.pop(email, None)

    audit_id = str(uuid4())
    now = datetime.now(timezone.utc)
    agent_audit_db[audit_id] = {
        "id": audit_id,
        "actor_email": email,
        "agent_id": None,
        "action": "monitoring_cache_cleared",
        "timestamp": now,
    }

    return CacheClearResponse(cleared=True, cleared_at=now)


@router.get("/performance", response_model=AgentPerformanceResponse)
def get_agent_performance(current_user: dict = Depends(get_current_user)):
    email = current_user["email"]
    cached = agent_monitoring_cache_db.get(email, {}).get("performance")
    if cached is not None:
        return cached
    result = _compute_performance(email)
    agent_monitoring_cache_db.setdefault(email, {})["performance"] = result
    return result