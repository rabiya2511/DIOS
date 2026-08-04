"""
Memory Retrieval router — search, retrieve, filter, rerank, recent,
favorites.
Matches the Retrieval section of the Memory APIs blueprint (6/6).
Queries the real memories owned by core_memory.py rather than a
separate store, so results here always reflect the same data
GET/PATCH/DELETE /memory/{id} operates on.

*** IMPORT (confirmed against core_memory.py) ***
This imports `memory_db` from app.routers.core_memory — note the
singular name, which breaks from the `{resource}s_db` convention used
elsewhere in this codebase (agents_db, tasks_db, deployments_db, etc.).
Confirmed directly against core_memory.py's source, not guessed.

*** ROUTING WARNING ***
GET /memory/recent and GET /memory/favorites are 2-segment paths
under /memory, the same shape as core_memory.py's GET /memory/{id}.
This router's app.include_router(...) call MUST be registered in
main.py BEFORE core_memory.router — same requirement already applied
to memory_context.router and conversation_memory.router after the
GET /memory/context collision. The four POST routes (/search,
/retrieve, /filter, /rerank) are unaffected regardless of order,
since core_memory.py has no POST /memory/{id} to collide with.

*** KNOWN GAP: favorites has no writer ***
favorite_memory_ids_db is defined in this file, but the blueprint's
Retrieval group has no endpoint that adds a memory to it — GET
/memory/favorites will always return empty until something writes to
this store. Flagged rather than silently inventing a non-blueprint
POST /memory/favorites/add endpoint to fill the gap.
"""

from typing import Literal

from fastapi import APIRouter, Depends

from app.schemas.memory_retrieval import (
    MemorySearchRequest,
    MemorySearchResult,
    MemorySearchResponse,
    MemoryRetrieveRequest,
    MemoryRetrieveResponse,
    MemoryFilterRequest,
    MemoryFilterResponse,
    MemoryRerankRequest,
    MemoryRerankResult,
    MemoryRerankResponse,
    RecentMemoriesResponse,
    FavoriteMemoriesResponse,
)
from app.core.security import get_current_user
from app.routers.core_memory import memory_db  # confirmed name, see IMPORT note above

router = APIRouter(prefix="/api/v1/memory", tags=["Memory Retrieval"])

# owner_email -> set of memory_id. No blueprint endpoint writes to this yet — see KNOWN GAP above.
favorite_memory_ids_db: dict[str, set[str]] = {}


def _owned_memories(email: str) -> list[dict]:
    return [m for m in memory_db.values() if m["owner_email"] == email]


@router.post("/search", response_model=MemorySearchResponse)
def search_memories(
    data: MemorySearchRequest,
    current_user: dict = Depends(get_current_user),
):
    """Naive substring search over content — no embeddings yet."""
    query_lower = data.query.lower()
    email = current_user["email"]

    results = []
    for m in memory_db.values():
        if m["owner_email"] != email:
            continue
        if data.memory_type is not None and m["memory_type"] != data.memory_type:
            continue
        if query_lower not in m["content"].lower():
            continue
        results.append(
            MemorySearchResult(
                id=m["id"],
                content=m["content"],
                memory_type=m["memory_type"],
                metadata=m["metadata"],
                status=m["status"],
                score=1.0,
            )
        )

    results = results[: data.limit]
    return MemorySearchResponse(query=data.query, total=len(results), results=results)


@router.post("/retrieve", response_model=MemoryRetrieveResponse)
def retrieve_memories(
    data: MemoryRetrieveRequest,
    current_user: dict = Depends(get_current_user),
):
    """Fetch specific memories by id — owner-scoped, missing/foreign ids silently skipped."""
    email = current_user["email"]
    items = [
        memory_db[mid] for mid in data.memory_ids
        if mid in memory_db and memory_db[mid]["owner_email"] == email
    ]
    return MemoryRetrieveResponse(total=len(items), items=items)


@router.post("/filter", response_model=MemoryFilterResponse)
def filter_memories(
    data: MemoryFilterRequest,
    current_user: dict = Depends(get_current_user),
):
    email = current_user["email"]
    items = []
    for m in memory_db.values():
        if m["owner_email"] != email:
            continue
        if data.memory_type is not None and m["memory_type"] != data.memory_type:
            continue
        if data.status is not None and m["status"] != data.status:
            continue
        if data.metadata_filters and not all(
            m["metadata"].get(k) == v for k, v in data.metadata_filters.items()
        ):
            continue
        if data.created_after is not None and m["created_at"] < data.created_after:
            continue
        if data.created_before is not None and m["created_at"] > data.created_before:
            continue
        items.append(m)

    return MemoryFilterResponse(total=len(items), items=items)


@router.post("/rerank", response_model=MemoryRerankResponse)
def rerank_memories(
    data: MemoryRerankRequest,
    current_user: dict = Depends(get_current_user),
):
    """Naive word-overlap scoring — no embeddings yet."""
    email = current_user["email"]
    candidates = _owned_memories(email)
    if data.memory_ids is not None:
        wanted = set(data.memory_ids)
        candidates = [m for m in candidates if m["id"] in wanted]

    query_words = set(data.query.lower().split())
    results = []
    for m in candidates:
        content_words = set(m["content"].lower().split())
        overlap = len(query_words & content_words)
        score = round(overlap / len(query_words), 2) if query_words else 0.0
        results.append(MemoryRerankResult(id=m["id"], content=m["content"], score=score))

    results.sort(key=lambda r: r.score, reverse=True)
    return MemoryRerankResponse(query=data.query, results=results)


@router.get("/recent", response_model=RecentMemoriesResponse)
def get_recent_memories(
    limit: int = 10,
    current_user: dict = Depends(get_current_user),
):
    items = _owned_memories(current_user["email"])
    items.sort(key=lambda m: m["updated_at"], reverse=True)
    items = items[:limit]
    return RecentMemoriesResponse(total=len(items), items=items)


@router.get("/favorites", response_model=FavoriteMemoriesResponse)
def get_favorite_memories(current_user: dict = Depends(get_current_user)):
    email = current_user["email"]
    favorite_ids = favorite_memory_ids_db.get(email, set())
    items = [memory_db[mid] for mid in favorite_ids if mid in memory_db]
    return FavoriteMemoriesResponse(total=len(items), items=items)