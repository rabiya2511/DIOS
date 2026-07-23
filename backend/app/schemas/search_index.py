"""
Pydantic schemas for the Search & Index domain (File & Storage APIs
blueprint). Operates over the existing files_db from fileslifecycle.py.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class FileSearchRequest(BaseModel):
    query: str


class FileIndexRequest(BaseModel):
    file_id: str


class IndexStatusResponse(BaseModel):
    indexed_count: int
    total_files: int
    last_indexed_at: datetime | None = None


class FileFilterRequest(BaseModel):
    status: str | None = None
    mime_type: str | None = None
    folder_id: str | None = None


class FileSortRequest(BaseModel):
    sort_by: str = "created_at"  # "created_at" | "updated_at" | "name" | "size_bytes"
    order: str = "desc"  # "asc" | "desc"


class FileSummary(BaseModel):
    id: str
    name: str
    folder_id: str | None = None
    size_bytes: int
    mime_type: str | None = None
    owner_email: str
    status: str
    created_at: datetime
    updated_at: datetime


class ReindexResponse(BaseModel):
    reindexed_count: int
    completed_at: datetime
    