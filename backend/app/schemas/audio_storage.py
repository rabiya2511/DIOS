"""
Schemas for the Audio Upload & Storage group of the Audio Services
APIs blueprint.
  POST   /api/v1/audio/upload
  GET    /api/v1/audio
  GET    /api/v1/audio/{id}
  PATCH  /api/v1/audio/{id}
  DELETE /api/v1/audio/{id}
  POST   /api/v1/audio/bulk-upload
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field


class AudioUpdateRequest(BaseModel):
    filename: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class AudioOut(BaseModel):
    id: str
    owner_email: EmailStr
    filename: str
    content_type: str
    size_bytes: int
    duration_seconds: Optional[float] = Field(
        None, description="Simulated — no real audio decoding is performed to measure this"
    )
    url: str = Field(..., description="Simulated storage URL — no real blob storage wired up")
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AudioListResponse(BaseModel):
    total: int
    items: List[AudioOut]


class AudioBulkUploadResponse(BaseModel):
    total_uploaded: int
    items: List[AudioOut]