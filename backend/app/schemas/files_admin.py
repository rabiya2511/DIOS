"""
Pydantic schemas for the File & Storage "Monitoring & Admin" domain
(GET /files/metrics, /files/logs, /files/health, /files/audit,
POST /files/cache/clear, PATCH /files/config, POST /files/export,
POST /files/import).

NOT to be confused with monitoring_metrics.py / app.schemas.monitoring_metrics,
which is a separate, platform-wide CPU/memory/disk/network monitoring domain.
This one is scoped specifically to the files domain.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class FileMetricsResponse(BaseModel):
    total_files: int
    total_size_bytes: int
    active_count: int
    archived_count: int
    avg_size_bytes: float


class FileLogEntry(BaseModel):
    file_id: str
    action: str  # "created" | "updated"
    timestamp: datetime


class FileAuditEntry(BaseModel):
    file_id: str
    owner_email: str
    action: str
    status: str
    timestamp: datetime


class FileHealthResponse(BaseModel):
    status: str
    total_files_tracked: int
    checked_at: datetime


class CacheClearResponse(BaseModel):
    cleared_count: int
    cleared_at: datetime


class FileConfigUpdateRequest(BaseModel):
    max_file_size_bytes: Optional[int] = None
    allowed_mime_types: Optional[List[str]] = None


class FileConfigResponse(BaseModel):
    max_file_size_bytes: int
    allowed_mime_types: List[str]


class FileExportRequest(BaseModel):
    format: str = "json"


class FileExportResponse(BaseModel):
    id: str
    owner_email: str
    format: str
    file_count: int
    status: str
    created_at: datetime


class FileImportItem(BaseModel):
    name: str
    folder_id: Optional[str] = None
    size_bytes: int = 0
    mime_type: Optional[str] = None


class FileImportRequest(BaseModel):
    files: List[FileImportItem]


class ImportedFileOut(BaseModel):
    id: str
    name: str
    folder_id: Optional[str] = None
    size_bytes: int
    mime_type: Optional[str] = None
    owner_email: str
    status: str
    created_at: datetime
    updated_at: datetime


class FileImportResponse(BaseModel):
    imported_count: int
    files: List[ImportedFileOut]