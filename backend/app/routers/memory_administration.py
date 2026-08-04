"""
Memory Administration router — metrics, health, logs, reindex, config,
backup.
Matches the Administration section of the Memory APIs blueprint (6/6).
All endpoints scoped to memories the caller owns, read from
core_memory.py's real memory_db rather than a separate store —
same approach as memory_retrieval.py.

*** ROUTING WARNING ***
GET /memory/metrics, GET /memory/health, GET /memory/logs, and
PATCH /memory/config are all 2-segment paths under /memory — the same
shape as core_memory.py's dynamic GET/PATCH /memory/{id}. This
router's app.include_router(...) call MUST be registered in main.py
BEFORE core_memory.router, same requirement already applied to
memory_context.router and memory_retrieval.router. POST /memory/reindex
and POST /memory/backup are unaffected regardless of order, since
core_memory.py has no POST /memory/{id} to collide with.

*** DESIGN NOTES ***
- reindex and backup are stubs: no real search index or backup storage
  exists yet, so both just count the caller's current memories and log
  the action. Real implementations would replace the body of
  reindex_memories/backup_memories without touching the schema.
- health's "degraded" threshold (>50% of memories archived) is an
  arbitrary heuristic, not from the blueprint — adjust freely.
- config has no GET endpoint in the blueprint, only PATCH — so config
  can only be read as a side effect of updating it (PATCH always
  returns the full current config, not just the changed fields).
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends

from app.schemas.memory_administration import (
    MemoryMetricsResponse,
    MemoryHealthResponse,
    MemoryLogListResponse,
    MemoryReindexResponse,
    MemoryConfigUpdateRequest,
    MemoryConfigResponse,
    MemoryBackupResponse,
)
from app.core.security import get_current_user
from app.routers.core_memory import memory_db

router = APIRouter(prefix="/api/v1/memory", tags=["Memory Administration"])

# id -> {id, owner_email, action, memory_id, detail, timestamp}
memory_admin_logs_db: dict[str, dict] = {}

# owner_email -> {retention_days, auto_archive_enabled, max_memories_per_user, updated_at}
memory_config_db: dict[str, dict] = {}

DEFAULT_CONFIG = {"retention_days": 90, "auto_archive_enabled": False, "max_memories_per_user": 1000}


def _owned_memories(email: str) -> list[dict]:
    return [m for m in memory_db.values() if m["owner_email"] == email]


def _get_or_create_config(email: str) -> dict:
    return memory_config_db.setdefault(email, {**DEFAULT_CONFIG, "updated_at": None})


def _log_action(email: str, action: str, memory_id: str | None = None, detail: str | None = None):
    log_id = str(uuid4())
    memory_admin_logs_db[log_id] = {
        "id": log_id,
        "owner_email": email,
        "action": action,
        "memory_id": memory_id,
        "detail": detail,
        "timestamp": datetime.now(timezone.utc),
    }


@router.get("/metrics", response_model=MemoryMetricsResponse)
def get_memory_metrics(current_user: dict = Depends(get_current_user)):
    owned = _owned_memories(current_user["email"])
    memory_types: dict[str, int] = {}
    for m in owned:
        memory_types[m["memory_type"]] = memory_types.get(m["memory_type"], 0) + 1

    return MemoryMetricsResponse(
        total_memories=len(owned),
        active_memories=sum(1 for m in owned if m["status"] == "active"),
        archived_memories=sum(1 for m in owned if m["status"] == "archived"),
        memory_types=memory_types,
        computed_at=datetime.now(timezone.utc),
    )


@router.get("/health", response_model=MemoryHealthResponse)
def get_memory_health(current_user: dict = Depends(get_current_user)):
    owned = _owned_memories(current_user["email"])
    total = len(owned)
    archived = sum(1 for m in owned if m["status"] == "archived")
    ratio = round(archived / total, 2) if total else 0.0
    status = "degraded" if ratio > 0.5 else "healthy"

    return MemoryHealthResponse(
        status=status,
        total_memories=total,
        archived_ratio=ratio,
        checked_at=datetime.now(timezone.utc),
    )


@router.get("/logs", response_model=MemoryLogListResponse)
def get_memory_logs(current_user: dict = Depends(get_current_user)):
    items = [l for l in memory_admin_logs_db.values() if l["owner_email"] == current_user["email"]]
    items.sort(key=lambda l: l["timestamp"], reverse=True)
    return MemoryLogListResponse(total=len(items), items=items)


@router.post("/reindex", response_model=MemoryReindexResponse)
def reindex_memories(current_user: dict = Depends(get_current_user)):
    email = current_user["email"]
    started_at = datetime.now(timezone.utc)
    owned = _owned_memories(email)
    completed_at = datetime.now(timezone.utc)

    _log_action(email, "reindex", detail=f"Reindexed {len(owned)} memories")

    return MemoryReindexResponse(
        reindexed_count=len(owned),
        started_at=started_at,
        completed_at=completed_at,
    )


@router.patch("/config", response_model=MemoryConfigResponse)
def update_memory_config(
    data: MemoryConfigUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    email = current_user["email"]
    config = _get_or_create_config(email)

    update_data = data.model_dump(exclude_unset=True)
    config.update(update_data)
    config["updated_at"] = datetime.now(timezone.utc)

    _log_action(email, "config_updated", detail=str(update_data))

    return MemoryConfigResponse(**config)


@router.post("/backup", response_model=MemoryBackupResponse)
def backup_memories(current_user: dict = Depends(get_current_user)):
    email = current_user["email"]
    owned = _owned_memories(email)
    backup_id = str(uuid4())
    created_at = datetime.now(timezone.utc)

    _log_action(email, "backup", detail=f"Backed up {len(owned)} memories")

    return MemoryBackupResponse(
        backup_id=backup_id,
        memory_count=len(owned),
        created_at=created_at,
    )