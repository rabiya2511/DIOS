"""
Schemas for Upload & Download domain.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class FileUploadRequest(BaseModel):
    name: str
    folder_id: Optional[str] = None
    size_bytes: Optional[int] = 0
    mime_type: Optional[str] = None


class ChunkUploadRequest(BaseModel):
    upload_id: str
    chunk_index: int
    total_chunks: int
    data_base64: str  # placeholder for actual binary chunk data


class ChunkUploadResponse(BaseModel):
    upload_id: str
    chunk_index: int
    received: bool


class UploadCompleteRequest(BaseModel):
    upload_id: str


class UploadedFileResponse(BaseModel):
    id: str
    name: str
    folder_id: Optional[str] = None
    size_bytes: int = 0
    mime_type: Optional[str] = None
    owner_email: str
    status: str
    created_at: datetime
    updated_at: datetime


class SignedUrlRequest(BaseModel):
    file_id: str
    expires_in_seconds: Optional[int] = 3600


class SignedUrlResponse(BaseModel):
    file_id: str
    url: str
    expires_at: datetime


class FileCopyRequest(BaseModel):
    file_id: str
    destination_folder_id: Optional[str] = None


class FileMoveRequest(BaseModel):
    file_id: str
    destination_folder_id: Optional[str] = None


class FileRenameRequest(BaseModel):
    file_id: str
    new_name: str