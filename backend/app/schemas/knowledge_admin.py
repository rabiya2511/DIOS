"""
Pydantic schemas for the Knowledge Administration domain
(Knowledge / RAG APIs blueprint).
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class KnowledgeConfigUpdateRequest(BaseModel):
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None
    embedding_model: Optional[str] = None
    auto_reindex: Optional[bool] = None


class KnowledgeConfigResponse(BaseModel):
    chunk_size: int
    chunk_overlap: int
    embedding_model: str
    auto_reindex: bool
    updated_at: datetime


class ReindexResponse(BaseModel):
    id: str
    status: str
    triggered_by: str
    started_at: datetime


class ValidateResponse(BaseModel):
    valid: bool
    issues: List[str]
    checked_at: datetime


class MigrateRequest(BaseModel):
    target_version: str


class MigrateResponse(BaseModel):
    id: str
    from_version: str
    to_version: str
    status: str
    migrated_at: datetime


class BackupResponse(BaseModel):
    id: str
    status: str
    created_at: datetime


class RestoreBackupRequest(BaseModel):
    backup_id: str


class RestoreBackupResponse(BaseModel):
    id: str
    backup_id: str
    status: str
    restored_at: datetime


class VersionResponse(BaseModel):
    api_version: str
    config_version: str
    last_migrated_at: Optional[datetime] = None