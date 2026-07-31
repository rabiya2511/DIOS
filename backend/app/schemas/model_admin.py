"""
Pydantic schemas for the Model Administration domain (Model Management
APIs blueprint).
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ModelIdBodyRequest(BaseModel):
    model_id: str


class ModelEnableResponse(BaseModel):
    model_id: str
    enabled: bool
    updated_at: datetime


class SyncResponse(BaseModel):
    id: str
    status: str
    synced_count: int
    triggered_by: str
    started_at: datetime


class ReindexResponse(BaseModel):
    id: str
    status: str
    triggered_by: str
    started_at: datetime


class ReloadResponse(BaseModel):
    id: str
    status: str
    reloaded_count: int
    triggered_by: str
    started_at: datetime


class AdminConfigUpdateRequest(BaseModel):
    default_provider: Optional[str] = None
    auto_sync_enabled: Optional[bool] = None
    max_models_per_user: Optional[int] = None


class AdminConfigResponse(BaseModel):
    default_provider: str
    auto_sync_enabled: bool
    max_models_per_user: int
    updated_at: datetime


class AuditEntry(BaseModel):
    id: str
    action: str
    actor_email: str
    detail: str
    timestamp: datetime