"""
Pydantic schemas for the Backup & Sync domain (File & Storage APIs blueprint).
"""

from datetime import datetime
from typing import Optional, Literal

from pydantic import BaseModel

SyncStatus = Literal["idle", "running", "stopped"]
BackupStatus = Literal["completed", "restored"]


class BackupCreateRequest(BaseModel):
    label: Optional[str] = None


class BackupOut(BaseModel):
    id: str
    owner_email: str
    label: Optional[str] = None
    file_count: int
    status: BackupStatus
    created_at: datetime


class BackupRestoreRequest(BaseModel):
    backup_id: str


class SyncStatusResponse(BaseModel):
    status: SyncStatus
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None


class ReplicationStatusResponse(BaseModel):
    status: SyncStatus
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None