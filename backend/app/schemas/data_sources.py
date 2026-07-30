"""
Schemas for the Data Sources group of the Knowledge/RAG APIs
blueprint.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Literal

from pydantic import BaseModel, EmailStr, Field

SourceStatus = Literal["active", "paused", "disconnected"]
SyncStatus = Literal["never_synced", "syncing", "synced", "failed"]


class DataSourceConnectRequest(BaseModel):
    name: str
    type: str = Field(..., description="e.g. 's3', 'gdrive', 'notion', 'confluence', 'website', 'database'")
    config: Dict[str, Any] = Field(default_factory=dict, description="Connection details (bucket, url, credentials ref, etc.)")


class DataSourceUpdateRequest(BaseModel):
    name: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    status: Optional[SourceStatus] = None


class DataSourceResponse(BaseModel):
    id: str
    owner_email: EmailStr
    name: str
    type: str
    config: Dict[str, Any]
    status: SourceStatus
    sync_status: SyncStatus
    last_synced_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class SourceSyncRequest(BaseModel):
    source_id: str


class SourceSyncResponse(BaseModel):
    source_id: str
    sync_status: SyncStatus
    triggered_at: datetime
    message: str


class SourceStatusEntry(BaseModel):
    source_id: str
    name: str
    sync_status: SyncStatus
    last_synced_at: Optional[datetime] = None


class SourceStatusResponse(BaseModel):
    total: int
    items: List[SourceStatusEntry]


class SourceWebhookRequest(BaseModel):
    source_id: str
    event: str = Field(..., description="e.g. 'file_updated', 'file_deleted', 'file_created'")
    payload: Dict[str, Any] = Field(default_factory=dict)


class SourceWebhookResponse(BaseModel):
    source_id: str
    event: str
    processed: bool
    new_sync_status: SyncStatus
    received_at: datetime