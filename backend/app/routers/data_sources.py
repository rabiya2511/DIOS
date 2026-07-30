"""
Data Sources router — connect, list, update, delete, sync, resync,
status, webhook. Matches the Data Sources section of the Knowledge/RAG
APIs blueprint (8/8). Only the source owner can update/delete/sync/
resync their own data source — same ownership model as conversations.py
and knowledge base router.

*** ROUTING NOTE ***
/sources/sync, /sources/resync, /sources/status, /sources/webhook are
literal paths under /api/v1/sources, registered BEFORE the dynamic
PATCH/DELETE /sources/{id} routes below — kept consistent with the
literal-before-dynamic convention even though none of this group's
literal paths actually collide with {id} (no GET /{id} exists here).

Sync/resync/webhook are simulated — no real external connector calls
(S3, Google Drive, Notion, etc.) are made. Swap in real integrations
before relying on this for anything beyond local dev.
"""

from datetime import datetime, timezone
from uuid import uuid4
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.schemas.data_sources import (
    DataSourceConnectRequest,
    DataSourceUpdateRequest,
    DataSourceResponse,
    SourceSyncRequest,
    SourceSyncResponse,
    SourceStatusResponse,
    SourceStatusEntry,
    SourceWebhookRequest,
    SourceWebhookResponse,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/sources", tags=["Data Sources"])

# id -> {id, owner_email, name, type, config, status, sync_status, last_synced_at, created_at, updated_at}
sources_db: dict[str, dict] = {}


def _get_source_or_404(source_id: str) -> dict:
    source = sources_db.get(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Data source not found")
    return source


def _require_owner(source: dict, email: str):
    if source["owner_email"] != email:
        raise HTTPException(status_code=403, detail="Only the data source owner can perform this action")


@router.get("", response_model=list[DataSourceResponse])
def list_sources(current_user: dict = Depends(get_current_user)):
    return [s for s in sources_db.values() if s["owner_email"] == current_user["email"]]


@router.post("/connect", response_model=DataSourceResponse, status_code=201)
def connect_source(
    data: DataSourceConnectRequest,
    current_user: dict = Depends(get_current_user),
):
    source_id = str(uuid4())
    now = datetime.now(timezone.utc)
    sources_db[source_id] = {
        "id": source_id,
        "owner_email": current_user["email"],
        "name": data.name,
        "type": data.type,
        "config": data.config,
        "status": "active",
        "sync_status": "never_synced",
        "last_synced_at": None,
        "created_at": now,
        "updated_at": now,
    }
    return sources_db[source_id]


# ─── Literal-path routes MUST come before any /{id} routes below ───

@router.post("/sync", response_model=SourceSyncResponse)
def sync_source(
    data: SourceSyncRequest,
    current_user: dict = Depends(get_current_user),
):
    """Trigger an incremental sync for a data source (simulated)."""
    source = _get_source_or_404(data.source_id)
    _require_owner(source, current_user["email"])

    now = datetime.now(timezone.utc)
    source["sync_status"] = "synced"
    source["last_synced_at"] = now
    source["updated_at"] = now

    return SourceSyncResponse(
        source_id=data.source_id, sync_status="synced", triggered_at=now,
        message="Incremental sync completed (simulated).",
    )


@router.post("/resync", response_model=SourceSyncResponse)
def resync_source(
    data: SourceSyncRequest,
    current_user: dict = Depends(get_current_user),
):
    """Trigger a full resync for a data source (simulated), discarding incremental state."""
    source = _get_source_or_404(data.source_id)
    _require_owner(source, current_user["email"])

    now = datetime.now(timezone.utc)
    source["sync_status"] = "synced"
    source["last_synced_at"] = now
    source["updated_at"] = now

    return SourceSyncResponse(
        source_id=data.source_id, sync_status="synced", triggered_at=now,
        message="Full resync completed (simulated).",
    )


@router.get("/status", response_model=SourceStatusResponse)
def get_sources_status(
    source_id: Optional[str] = Query(None, description="Filter to a single source"),
    current_user: dict = Depends(get_current_user),
):
    """Get sync status for one source (if source_id given) or all of the caller's sources."""
    owned = [s for s in sources_db.values() if s["owner_email"] == current_user["email"]]

    if source_id:
        owned = [s for s in owned if s["id"] == source_id]
        if not owned:
            raise HTTPException(status_code=404, detail="Data source not found")

    items = [
        SourceStatusEntry(
            source_id=s["id"], name=s["name"],
            sync_status=s["sync_status"], last_synced_at=s["last_synced_at"],
        )
        for s in owned
    ]
    return SourceStatusResponse(total=len(items), items=items)


@router.post("/webhook", response_model=SourceWebhookResponse)
def source_webhook(
    data: SourceWebhookRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Receive a (simulated) inbound webhook notification from an external
    data source about a change (file created/updated/deleted), marking
    the source as due for sync.
    """
    source = _get_source_or_404(data.source_id)
    _require_owner(source, current_user["email"])

    now = datetime.now(timezone.utc)
    source["sync_status"] = "syncing"
    source["updated_at"] = now

    return SourceWebhookResponse(
        source_id=data.source_id, event=data.event, processed=True,
        new_sync_status="syncing", received_at=now,
    )


# ─── Dynamic /{id} routes come LAST ───

@router.patch("/{id}", response_model=DataSourceResponse)
def update_source(
    id: str,
    data: DataSourceUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    source = _get_source_or_404(id)
    _require_owner(source, current_user["email"])

    update_data = data.model_dump(exclude_unset=True)
    source.update(update_data)
    source["updated_at"] = datetime.now(timezone.utc)
    return source


@router.delete("/{id}", status_code=204)
def delete_source(id: str, current_user: dict = Depends(get_current_user)):
    source = _get_source_or_404(id)
    _require_owner(source, current_user["email"])
    del sources_db[id]
    return None