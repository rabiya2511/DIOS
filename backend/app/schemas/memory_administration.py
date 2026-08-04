"""
Schemas for the Administration group of the Memory APIs blueprint.
"""

from datetime import datetime
from typing import Optional, List, Dict, Literal

from pydantic import BaseModel, Field

HealthStatus = Literal["healthy", "degraded"]


class MemoryMetricsResponse(BaseModel):
    total_memories: int
    active_memories: int
    archived_memories: int
    memory_types: Dict[str, int]
    computed_at: datetime


class MemoryHealthResponse(BaseModel):
    status: HealthStatus
    total_memories: int
    archived_ratio: float = Field(..., ge=0.0, le=1.0)
    checked_at: datetime


class MemoryLogEntry(BaseModel):
    id: str
    action: str
    memory_id: Optional[str] = None
    detail: Optional[str] = None
    timestamp: datetime


class MemoryLogListResponse(BaseModel):
    total: int
    items: List[MemoryLogEntry]


class MemoryReindexResponse(BaseModel):
    reindexed_count: int
    started_at: datetime
    completed_at: datetime


class MemoryConfigUpdateRequest(BaseModel):
    retention_days: Optional[int] = Field(None, ge=1)
    auto_archive_enabled: Optional[bool] = None
    max_memories_per_user: Optional[int] = Field(None, ge=1)


class MemoryConfigResponse(BaseModel):
    retention_days: int
    auto_archive_enabled: bool
    max_memories_per_user: int
    updated_at: Optional[datetime] = None


class MemoryBackupResponse(BaseModel):
    backup_id: str
    memory_count: int
    created_at: datetime