"""
Vector Index router — build/reindex/delete/get index, optimize, compact,
stats, snapshot.
Matches the Vector Index section of the Knowledge / RAG APIs blueprint
(8/8).

IMPORTANT — READ BEFORE RELYING ON ANY RESULT FROM THIS ROUTER:
This is entirely SIMULATED. There is no real vector database (FAISS,
Pinecone, pgvector, Qdrant, etc.) and no real embeddings anywhere here.
"vector_count" is just len(source_ids) from whatever you send in. "size_mb"
is a real arithmetic estimate (vector_count * dimensions * 4 bytes, the
standard float32 embedding size), but it's sizing IMAGINARY vectors, not
measuring anything real. "optimize" and "compact" apply arbitrary
percentage reductions to simulate what those operations conceptually do,
not real index compression or dead-vector removal.

Scope: ONE index per caller (owner_email), not multiple named indexes —
the blueprint gives no {id} path for any of these endpoints, so there's
nothing to key multiple indexes by. Building a new index (POST
/vectors/index) when one already exists REPLACES it entirely.

No route-ordering concerns: /vectors/index, /vectors/reindex,
/vectors/optimize, /vectors/compact, /vectors/stats, /vectors/snapshot
are all flat, distinct literal paths — GET/POST/DELETE all share the
literal "/vectors/index" path but differ by HTTP method, which FastAPI
resolves without any ordering issues (different methods on the same
literal path don't conflict, unlike literal-vs-dynamic-segment cases
elsewhere in this codebase).
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.vector_index import (
    VectorIndexBuildRequest,
    VectorIndexOut,
    VectorIndexStatsResponse,
    VectorSnapshotResponse,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/vectors", tags=["Vector Index"])

# owner_email -> index state dict
vector_indexes_db: dict[str, dict] = {}

# owner_email -> [{id, vector_count, size_mb, created_at}]
vector_snapshots_db: dict[str, list[dict]] = {}

BYTES_PER_FLOAT32 = 4


def _calc_size_mb(vector_count: int, dimensions: int) -> float:
    return round((vector_count * dimensions * BYTES_PER_FLOAT32) / (1024 * 1024), 4)


def _get_index_or_404(email: str) -> dict:
    index = vector_indexes_db.get(email)
    if not index or index["status"] == "empty":
        raise HTTPException(status_code=404, detail="No vector index exists for this account")
    return index


@router.post("/index", response_model=VectorIndexOut, status_code=201)
def build_vector_index(
    data: VectorIndexBuildRequest,
    current_user: dict = Depends(get_current_user),
):
    email = current_user["email"]
    now = datetime.now(timezone.utc)
    vector_count = len(data.source_ids)
    vector_indexes_db[email] = {
        "status": "ready",
        "vector_count": vector_count,
        "dimensions": data.dimensions,
        "size_mb": _calc_size_mb(vector_count, data.dimensions),
        "owner_email": email,
        "last_indexed_at": now,
        "last_optimized_at": None,
        "last_compacted_at": None,
    }
    return vector_indexes_db[email]


@router.post("/reindex", response_model=VectorIndexOut)
def reindex_vector_index(current_user: dict = Depends(get_current_user)):
    index = _get_index_or_404(current_user["email"])
    index["last_indexed_at"] = datetime.now(timezone.utc)
    index["size_mb"] = _calc_size_mb(index["vector_count"], index["dimensions"])
    return index


@router.delete("/index", status_code=204)
def delete_vector_index(current_user: dict = Depends(get_current_user)):
    email = current_user["email"]
    _get_index_or_404(email)
    vector_indexes_db[email] = {
        "status": "empty",
        "vector_count": 0,
        "dimensions": 0,
        "size_mb": 0.0,
        "owner_email": email,
        "last_indexed_at": None,
        "last_optimized_at": None,
        "last_compacted_at": None,
    }
    return None


@router.get("/index", response_model=VectorIndexOut)
def get_vector_index(current_user: dict = Depends(get_current_user)):
    return _get_index_or_404(current_user["email"])


@router.post("/optimize", response_model=VectorIndexOut)
def optimize_vector_index(current_user: dict = Depends(get_current_user)):
    index = _get_index_or_404(current_user["email"])
    # STUB: simulate ~15% size reduction from optimization — not real compression.
    index["size_mb"] = round(index["size_mb"] * 0.85, 4)
    index["last_optimized_at"] = datetime.now(timezone.utc)
    return index


@router.post("/compact", response_model=VectorIndexOut)
def compact_vector_index(current_user: dict = Depends(get_current_user)):
    index = _get_index_or_404(current_user["email"])
    # STUB: simulate removing ~5% of vectors as "stale/deleted" — not a real compaction pass.
    removed = max(0, round(index["vector_count"] * 0.05))
    index["vector_count"] = max(0, index["vector_count"] - removed)
    index["size_mb"] = _calc_size_mb(index["vector_count"], index["dimensions"])
    index["last_compacted_at"] = datetime.now(timezone.utc)
    return index


@router.get("/stats", response_model=VectorIndexStatsResponse)
def get_vector_index_stats(current_user: dict = Depends(get_current_user)):
    email = current_user["email"]
    index = vector_indexes_db.get(email, {
        "status": "empty", "vector_count": 0, "dimensions": 0, "size_mb": 0.0,
        "last_indexed_at": None, "last_optimized_at": None, "last_compacted_at": None,
    })
    snapshots = vector_snapshots_db.get(email, [])
    return VectorIndexStatsResponse(
        status=index["status"],
        vector_count=index["vector_count"],
        dimensions=index["dimensions"],
        size_mb=index["size_mb"],
        last_indexed_at=index["last_indexed_at"],
        last_optimized_at=index["last_optimized_at"],
        last_compacted_at=index["last_compacted_at"],
        snapshot_count=len(snapshots),
    )


@router.post("/snapshot", response_model=VectorSnapshotResponse, status_code=201)
def snapshot_vector_index(current_user: dict = Depends(get_current_user)):
    email = current_user["email"]
    index = _get_index_or_404(email)
    snapshot = {
        "id": str(uuid4()),
        "vector_count": index["vector_count"],
        "size_mb": index["size_mb"],
        "created_at": datetime.now(timezone.utc),
    }
    vector_snapshots_db.setdefault(email, []).append(snapshot)
    return snapshot