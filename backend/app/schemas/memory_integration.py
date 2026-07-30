"""
Memory Integration router — attach, detach, list, search, update,
summarize memories on an agent; build/clear an agent's built context.
Matches the Memory Integration section of the Agents & Planning APIs
blueprint (8/8). Only the record owner can detach/update/summarize/
search/build/clear their own agent's memory — same ownership model as
agent_lifecycle.py / planning.py / tasks.py / tools.py / reasoning.py.

*** ROUTING WARNING ***
This router shares the /api/v1/agents prefix with agent_lifecycle.py,
which owns GET /agents/{id}. This file's GET /agents/memory is a
single path segment, so it collides with that dynamic route: whichever
router FastAPI matches first wins. To keep GET /agents/memory from
being swallowed by GET /agents/{id} (with "memory" treated as the id),
this router's app.include_router(...) call MUST be added to main.py
BEFORE agent_lifecycle.router's call. All other routes here are two
segments (e.g. /agents/memory/attach, /agents/context/build) and don't
collide with /agents/{id} regardless of order.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.memory_integration import (
    MemoryAttachRequest,
    MemoryDetachRequest,
    MemoryDetachResponse,
    AgentMemoryResponse,
    AgentMemoryListResponse,
    MemorySearchRequest,
    MemorySearchResult,
    MemorySearchResponse,
    MemoryUpdateRequest,
    MemorySummarizeRequest,
    MemorySummarizeResponse,
    ContextBuildRequest,
    ContextBuildResponse,
    ContextClearRequest,
    ContextClearResponse,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/agents", tags=["Memory Integration"])

# id -> {id, owner_email, agent_id, memory_id, label, content, attached_at, updated_at}
agent_memories_db: dict[str, dict] = {}

# agent_id -> {agent_id, owner_email, context, memory_ids_used, built_at}
agent_context_db: dict[str, dict] = {}


def _find_memory_record(agent_id: str, memory_id: str, owner_email: str) -> dict:
    for record in agent_memories_db.values():
        if record["agent_id"] == agent_id and record["memory_id"] == memory_id and record["owner_email"] == owner_email:
            return record
    raise HTTPException(status_code=404, detail="Memory attachment not found for this agent")


@router.post("/memory/attach", response_model=AgentMemoryResponse, status_code=201)
def attach_memory(
    data: MemoryAttachRequest,
    current_user: dict = Depends(get_current_user),
):
    record_id = str(uuid4())
    now = datetime.now(timezone.utc)
    agent_memories_db[record_id] = {
        "id": record_id,
        "owner_email": current_user["email"],
        "agent_id": data.agent_id,
        "memory_id": data.memory_id,
        "label": data.label,
        "content": data.content,
        "attached_at": now,
        "updated_at": now,
    }
    return agent_memories_db[record_id]


@router.post("/memory/detach", response_model=MemoryDetachResponse)
def detach_memory(
    data: MemoryDetachRequest,
    current_user: dict = Depends(get_current_user),
):
    record = _find_memory_record(data.agent_id, data.memory_id, current_user["email"])
    del agent_memories_db[record["id"]]
    return MemoryDetachResponse(agent_id=data.agent_id, memory_id=data.memory_id, detached=True)


@router.get("/memory", response_model=AgentMemoryListResponse)
def list_agent_memories(
    agent_id: str | None = None,
    current_user: dict = Depends(get_current_user),
):
    items = [
        m for m in agent_memories_db.values()
        if m["owner_email"] == current_user["email"] and (agent_id is None or m["agent_id"] == agent_id)
    ]
    return AgentMemoryListResponse(total=len(items), items=items)


@router.post("/memory/search", response_model=MemorySearchResponse)
def search_agent_memories(
    data: MemorySearchRequest,
    current_user: dict = Depends(get_current_user),
):
    """Naive substring search over label/content — no embeddings yet."""
    query_lower = data.query.lower()
    results: list[MemorySearchResult] = []

    for m in agent_memories_db.values():
        if m["owner_email"] != current_user["email"]:
            continue
        if data.agent_id is not None and m["agent_id"] != data.agent_id:
            continue

        haystack = f"{m.get('label') or ''} {m.get('content') or ''}".lower()
        if query_lower not in haystack:
            continue

        label_hit = query_lower in (m.get("label") or "").lower()
        content_hit = query_lower in (m.get("content") or "").lower()
        score = 1.0 if (label_hit and content_hit) else 0.6

        results.append(
            MemorySearchResult(
                id=m["id"],
                agent_id=m["agent_id"],
                memory_id=m["memory_id"],
                label=m.get("label"),
                content=m.get("content"),
                score=score,
            )
        )

    results.sort(key=lambda r: r.score, reverse=True)
    return MemorySearchResponse(query=data.query, total=len(results), results=results)


@router.post("/memory/update", response_model=AgentMemoryResponse)
def update_agent_memory(
    data: MemoryUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    record = _find_memory_record(data.agent_id, data.memory_id, current_user["email"])

    if data.label is not None:
        record["label"] = data.label
    if data.content is not None:
        record["content"] = data.content
    record["updated_at"] = datetime.now(timezone.utc)
    return record


@router.post("/memory/summarize", response_model=MemorySummarizeResponse)
def summarize_agent_memories(
    data: MemorySummarizeRequest,
    current_user: dict = Depends(get_current_user),
):
    """Naive concatenation-based summary — no LLM call yet."""
    memories = [
        m for m in agent_memories_db.values()
        if m["owner_email"] == current_user["email"] and m["agent_id"] == data.agent_id
    ]

    if not memories:
        summary = f"No memories are attached to agent {data.agent_id}."
    else:
        bullets = [f"- {m.get('label') or m['memory_id']}: {m.get('content') or 'no content stored'}" for m in memories]
        summary = f"{len(memories)} memory item(s) attached to agent {data.agent_id}:\n" + "\n".join(bullets)

    return MemorySummarizeResponse(
        agent_id=data.agent_id,
        memory_count=len(memories),
        summary=summary,
        summarized_at=datetime.now(timezone.utc),
    )


@router.post("/context/build", response_model=ContextBuildResponse)
def build_agent_context(
    data: ContextBuildRequest,
    current_user: dict = Depends(get_current_user),
):
    candidates = [
        m for m in agent_memories_db.values()
        if m["owner_email"] == current_user["email"] and m["agent_id"] == data.agent_id
    ]
    if data.memory_ids is not None:
        wanted = set(data.memory_ids)
        candidates = [m for m in candidates if m["memory_id"] in wanted]

    candidates = candidates[: data.max_items]

    context_parts = [m.get("content") or m.get("label") or m["memory_id"] for m in candidates]
    context = "\n".join(context_parts) if context_parts else ""
    memory_ids_used = [m["memory_id"] for m in candidates]
    built_at = datetime.now(timezone.utc)

    agent_context_db[data.agent_id] = {
        "agent_id": data.agent_id,
        "owner_email": current_user["email"],
        "context": context,
        "memory_ids_used": memory_ids_used,
        "built_at": built_at,
    }

    return ContextBuildResponse(
        agent_id=data.agent_id,
        context=context,
        memory_ids_used=memory_ids_used,
        built_at=built_at,
    )


@router.post("/context/clear", response_model=ContextClearResponse)
def clear_agent_context(
    data: ContextClearRequest,
    current_user: dict = Depends(get_current_user),
):
    existing = agent_context_db.get(data.agent_id)
    if existing and existing["owner_email"] != current_user["email"]:
        raise HTTPException(status_code=403, detail="Only the context owner can clear it")

    agent_context_db.pop(data.agent_id, None)
    return ContextClearResponse(agent_id=data.agent_id, cleared=True, cleared_at=datetime.now(timezone.utc))