"""
Knowledge & RAG router — search, retrieve, rerank, index, upload, remove,
sources, refresh.
Matches the Knowledge & RAG section of the AI Chat APIs blueprint (8/8).
Simulated — substring matching stands in for real vector similarity search.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.chat_rag import (
    RagSearchRequest,
    RagResultOut,
    RagRetrieveRequest,
    RagRerankRequest,
    RagIndexRequest,
    RagSourceOut,
    RagUploadRequest,
    RagRemoveRequest,
    RagRefreshResponse,
)
from app.models.user import rag_sources_db
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/chat/rag", tags=["AI Chat: Knowledge & RAG"])


def _simulated_search(query: str, owner_email: str, top_k: int) -> list[dict]:
    query_lower = query.lower()
    results = []
    for src in rag_sources_db.values():
        if src["owner_email"] != owner_email:
            continue
        if query_lower in src["content"].lower() or query_lower in src["title"].lower():
            snippet = src["content"][:150]
            score = round(min(1.0, len(query_lower) / max(len(src["content"]), 1) + 0.5), 2)
            results.append({"source_id": src["id"], "title": src["title"], "snippet": snippet, "score": score})
    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:top_k]


@router.post("/search", response_model=list[RagResultOut])
def search_knowledge(
    data: RagSearchRequest,
    current_user: dict = Depends(get_current_user),
):
    return _simulated_search(data.query, current_user["email"], data.top_k)


@router.post("/retrieve", response_model=list[RagResultOut])
def retrieve_knowledge(
    data: RagRetrieveRequest,
    current_user: dict = Depends(get_current_user),
):
    return _simulated_search(data.query, current_user["email"], data.top_k)


@router.post("/rerank", response_model=list[RagResultOut])
def rerank_results(
    data: RagRerankRequest,
    current_user: dict = Depends(get_current_user),
):
    # STUB: real version uses a cross-encoder; here we just re-sort by
    # how much of the query appears in the snippet, as a stand-in signal.
    query_lower = data.query.lower()
    reranked = sorted(
        data.results,
        key=lambda r: r.snippet.lower().count(query_lower),
        reverse=True,
    )
    return reranked


@router.post("/index", response_model=RagSourceOut, status_code=201)
def index_source(
    data: RagIndexRequest,
    current_user: dict = Depends(get_current_user),
):
    source_id = str(uuid4())
    now = datetime.now(timezone.utc)
    rag_sources_db[source_id] = {
        "id": source_id,
        "owner_email": current_user["email"],
        "title": data.title,
        "content": data.content,
        "indexed_at": now,
        "created_at": now,
    }
    return rag_sources_db[source_id]


@router.post("/upload", response_model=RagSourceOut, status_code=201)
def upload_source(
    data: RagUploadRequest,
    current_user: dict = Depends(get_current_user),
):
    source_id = str(uuid4())
    now = datetime.now(timezone.utc)
    rag_sources_db[source_id] = {
        "id": source_id,
        "owner_email": current_user["email"],
        "title": data.title,
        "content": data.content,
        "indexed_at": now,
        "created_at": now,
    }
    return rag_sources_db[source_id]


@router.post("/remove", status_code=204)
def remove_source(
    data: RagRemoveRequest,
    current_user: dict = Depends(get_current_user),
):
    src = rag_sources_db.get(data.source_id)
    if not src:
        raise HTTPException(status_code=404, detail="Source not found")
    if src["owner_email"] != current_user["email"]:
        raise HTTPException(status_code=403, detail="Only the source owner can perform this action")
    del rag_sources_db[data.source_id]
    return None


@router.get("/sources", response_model=list[RagSourceOut])
def list_sources(current_user: dict = Depends(get_current_user)):
    return [s for s in rag_sources_db.values() if s["owner_email"] == current_user["email"]]


@router.post("/refresh", response_model=RagRefreshResponse)
def refresh_index(current_user: dict = Depends(get_current_user)):
    now = datetime.now(timezone.utc)
    count = 0
    for src in rag_sources_db.values():
        if src["owner_email"] == current_user["email"]:
            src["indexed_at"] = now
            count += 1
    return RagRefreshResponse(refreshed_count=count, timestamp=now)