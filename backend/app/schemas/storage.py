"""
Pydantic schemas for the Storage domain.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class BucketCreateRequest(BaseModel):
    name: str
    region: str = "us-east-1"


class BucketUpdateRequest(BaseModel):
    name: Optional[str] = None
    region: Optional[str] = None


class BucketOut(BaseModel):
    id: str
    name: str
    owner_email: str
    region: str
    created_at: datetime


class StorageUsageOut(BaseModel):
    total_files: int
    total_bytes: int
    bucket_count: int


class QuotaOut(BaseModel):
    limit_bytes: int
    used_bytes: int


class QuotaUpdateRequest(BaseModel):
    limit_bytes: int


class MigrateRequest(BaseModel):
    bucket_id: str
    target_region: str


class MigrateResponse(BaseModel):
    bucket_id: str
    target_region: str
    status: str
    started_at: datetime