"""
Search & Index router — search, index, reindex, filter, sort, recent, favorites.
Matches the Search & Index section of the File & Storage APIs blueprint (8/8).
Operates over the existing files_db from fileslifecycle.py.

IMPORTANT: Shares the /api/v1/files prefix with fileslifecycle.router.
This router MUST be included in main.py BEFORE fileslifecycle.router,
so literal paths (/search, /index, /filter, /sort, /recent, /favorites)
are matched before fileslifecycle's dynamic GET /files/{id}.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query

from app.schemas.search_index import (
    FileSearchRequest,
    FileIndexRequest,
    IndexStatusResponse,
    FileFilterRequest,
    FileSortRequest,
    FileSummary,
    ReindexResponse,
)
from app.core.security import get_current_user
from app.routers.fileslifecycle import files_db, _get_file_or_404, _require_owner

router = APIRouter(prefix="/api/v1/files", tags=["Search & Index"])

# file_id -> indexed_at datetime
index_db: dict[str, datetime] = {}

# email -> set of favorited file_ids (no create endpoint in this blueprint;
# stays empty unless another domain populates it)
favorites_db: dict[str, set] = {}


def _owned_files(email: str) -> list[dict]:
    return [f for f in files_db.values() if f["owner_email"] == email]


@router.post("/search", response_model=list[FileSummary])
def search_files(
    data: FileSearchRequest,
    current_user: dict = Depends(get_current_user),
):
    query = data.query.lower()
    return [
        f for f in _owned_files(current_user["email"])
        if query in f["name"].lower()
    ]


@router.post("/index", response_model=IndexStatusResponse, status_code=201)
def index_file(
    data: FileIndexRequest,
    current_user: dict = Depends(get_current_user),
):
    file = _get_file_or_404(data.file_id)
    _require_owner(file, current_user["email"])
    now = datetime.now(timezone.utc)
    index_db[data.file_id] = now

    owned_ids = {f["id"] for f in _owned_files(current_user["email"])}
    indexed_owned = {fid: ts for fid, ts in index_db.items() if fid in owned_ids}
    return IndexStatusResponse(
        indexed_count=len(indexed_owned),
        total_files=len(owned_ids),
        last_indexed_at=now,
    )



@router.post("/reindex", response_model=ReindexResponse)
def reindex_files(current_user: dict = Depends(get_current_user)):
    now = datetime.now(timezone.utc)
    owned = _owned_files(current_user["email"])
    for f in owned:
        index_db[f["id"]] = now
    return ReindexResponse(reindexed_count=len(owned), completed_at=now)


@router.get("/index/status", response_model=IndexStatusResponse)
def index_status(current_user: dict = Depends(get_current_user)):
    owned_ids = {f["id"] for f in _owned_files(current_user["email"])}
    indexed_owned = {fid: ts for fid, ts in index_db.items() if fid in owned_ids}
    last_indexed = max(indexed_owned.values()) if indexed_owned else None
    return IndexStatusResponse(
        indexed_count=len(indexed_owned),
        total_files=len(owned_ids),
        last_indexed_at=last_indexed,
    )


@router.post("/filter", response_model=list[FileSummary])
def filter_files(
    data: FileFilterRequest,
    current_user: dict = Depends(get_current_user),
):
    results = _owned_files(current_user["email"])
    if data.status:
        results = [f for f in results if f["status"] == data.status]
    if data.mime_type:
        results = [f for f in results if f["mime_type"] == data.mime_type]
    if data.folder_id:
        results = [f for f in results if f["folder_id"] == data.folder_id]
    return results


@router.post("/sort", response_model=list[FileSummary])
def sort_files(
    data: FileSortRequest,
    current_user: dict = Depends(get_current_user),
):
    valid_fields = {"created_at", "updated_at", "name", "size_bytes"}
    sort_by = data.sort_by if data.sort_by in valid_fields else "created_at"
    reverse = data.order != "asc"
    results = _owned_files(current_user["email"])
    return sorted(results, key=lambda f: f[sort_by], reverse=reverse)


@router.get("/recent", response_model=list[FileSummary])
def recent_files(
    limit: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    results = _owned_files(current_user["email"])
    results.sort(key=lambda f: f["updated_at"], reverse=True)
    return results[:limit]


@router.get("/favorites", response_model=list[FileSummary])
def list_favorites(current_user: dict = Depends(get_current_user)):
    favorite_ids = favorites_db.get(current_user["email"], set())
    return [f for f in _owned_files(current_user["email"]) if f["id"] in favorite_ids]