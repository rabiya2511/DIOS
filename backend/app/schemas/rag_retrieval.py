"""
RAG Retrieval router — search, retrieve, filter, query, hybrid-search,
semantic-search, keyword-search, history.
Matches the Retrieval section of the Knowledge / RAG APIs blueprint (8/8).

IMPORTANT — READ BEFORE RELYING ON ANY RESULT FROM THIS ROUTER:
This is entirely SIMULATED. There is no real document corpus, no real
embeddings, and no real search index (vector or keyword) anywhere here —
this codebase doesn't have the Knowledge Base / Documents sections built
yet for it to search over. Every "result" is deterministically generated
from the query string itself (e.g. "Simulated passage 1 relevant to
'{query}'" with a descending fake score), NOT retrieved from any real
data. /rag/query's "answer" field is a template string, not a real
generated response from any model. Wire this up to a real vector store +
retrieval pipeline (and the actual Documents/Knowledge Base domains) when
those exist, before trusting any of this for real retrieval.

Every call across all 7 query-type endpoints is logged to a per-caller
history list, so GET /rag/history reflects real usage of this stub, even
though the results themselves are fake.

No route-ordering concerns: every path here is a flat, distinct literal
path under /api/v1/rag — no /{id} anywhere in this section.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends

from app.schemas.rag_retrieval import (
    RagResultItem,
    RagSearchRequest,
    RagSearchResponse,
    RagFilterRequest,
    RagQueryRequest,
    RagQueryResponse,
    RagHybridSearchRequest,
    RagHistoryEntry,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/rag", tags=["RAG Retrieval"])

# owner_email -> [{id, endpoint, query, result_count, created_at}]
rag_history_db: dict[str, list[dict]] = {}


def _generate_results(query: str, top_k: int, note: str = "") -> list[RagResultItem]:
    """STUB — deterministically fabricated results, not real retrieval."""
    n = max(0, min(top_k, 20))
    suffix = f" ({note})" if note else ""
    return [
        RagResultItem(
            id=str(uuid4()),
            source_id=f"doc-{i + 1}",
            content_snippet=f"Simulated passage {i + 1} relevant to '{query}'{suffix}",
            score=round(max(0.0, 0.95 - i * 0.07), 2),
        )
        for i in range(n)
    ]


def _log_history(email: str, endpoint: str, query: str, result_count: int):
    rag_history_db.setdefault(email, []).append({
        "id": str(uuid4()),
        "endpoint": endpoint,
        "query": query,
        "result_count": result_count,
        "created_at": datetime.now(timezone.utc),
    })


@router.post("/search", response_model=RagSearchResponse, status_code=201)
def rag_search(data: RagSearchRequest, current_user: dict = Depends(get_current_user)):
    results = _generate_results(data.query, data.top_k)
    now = datetime.now(timezone.utc)
    _log_history(current_user["email"], "search", data.query, len(results))
    return RagSearchResponse(query=data.query, method="search", results=results, created_at=now)


@router.post("/retrieve", response_model=RagSearchResponse, status_code=201)
def rag_retrieve(data: RagSearchRequest, current_user: dict = Depends(get_current_user)):
    results = _generate_results(data.query, data.top_k)
    now = datetime.now(timezone.utc)
    _log_history(current_user["email"], "retrieve", data.query, len(results))
    return RagSearchResponse(query=data.query, method="retrieve", results=results, created_at=now)


@router.post("/filter", response_model=RagSearchResponse, status_code=201)
def rag_filter(data: RagFilterRequest, current_user: dict = Depends(get_current_user)):
    note = f"filtered by {data.filters}" if data.filters else ""
    results = _generate_results(data.query, data.top_k, note=note)
    now = datetime.now(timezone.utc)
    _log_history(current_user["email"], "filter", data.query, len(results))
    return RagSearchResponse(query=data.query, method="filter", results=results, created_at=now)


@router.post("/query", response_model=RagQueryResponse, status_code=201)
def rag_query(data: RagQueryRequest, current_user: dict = Depends(get_current_user)):
    results = _generate_results(data.query, data.top_k)
    # STUB — template string, not a real generated answer.
    answer = f"[simulated] Based on {len(results)} retrieved passages, here is a summary answer to: {data.query}"
    now = datetime.now(timezone.utc)
    _log_history(current_user["email"], "query", data.query, len(results))
    return RagQueryResponse(query=data.query, results=results, answer=answer, created_at=now)


@router.post("/hybrid-search", response_model=RagSearchResponse, status_code=201)
def rag_hybrid_search(data: RagHybridSearchRequest, current_user: dict = Depends(get_current_user)):
    note = f"hybrid, keyword_weight={data.keyword_weight}"
    results = _generate_results(data.query, data.top_k, note=note)
    now = datetime.now(timezone.utc)
    _log_history(current_user["email"], "hybrid-search", data.query, len(results))
    return RagSearchResponse(query=data.query, method="hybrid-search", results=results, created_at=now)


@router.post("/semantic-search", response_model=RagSearchResponse, status_code=201)
def rag_semantic_search(data: RagSearchRequest, current_user: dict = Depends(get_current_user)):
    results = _generate_results(data.query, data.top_k, note="semantic")
    now = datetime.now(timezone.utc)
    _log_history(current_user["email"], "semantic-search", data.query, len(results))
    return RagSearchResponse(query=data.query, method="semantic-search", results=results, created_at=now)


@router.post("/keyword-search", response_model=RagSearchResponse, status_code=201)
def rag_keyword_search(data: RagSearchRequest, current_user: dict = Depends(get_current_user)):
    results = _generate_results(data.query, data.top_k, note="keyword")
    now = datetime.now(timezone.utc)
    _log_history(current_user["email"], "keyword-search", data.query, len(results))
    return RagSearchResponse(query=data.query, method="keyword-search", results=results, created_at=now)


@router.get("/history", response_model=list[RagHistoryEntry])
def rag_history(current_user: dict = Depends(get_current_user)):
    entries = rag_history_db.get(current_user["email"], [])
    entries_sorted = sorted(entries, key=lambda e: e["created_at"], reverse=True)
    return [RagHistoryEntry(**e) for e in entries_sorted]