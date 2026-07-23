"""
Schemas for Metadata domain (File & Storage blueprint).
Mounted at /api/v1/files/metadata.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class MetadataResponse(BaseModel):
    file_id: str
    tags: list[str] = []
    labels: list[str] = []
    classification: Optional[str] = None
    custom_fields: dict = {}
    updated_at: datetime


class MetadataUpdateRequest(BaseModel):
    file_id: str
    custom_fields: dict


class TagsAddRequest(BaseModel):
    file_id: str
    tags: list[str]


class TagsRemoveRequest(BaseModel):
    file_id: str
    tags: list[str]


class ClassifyRequest(BaseModel):
    file_id: str
    classification: str  # e.g. "confidential", "internal", "public"


class LabelsAddRequest(BaseModel):
    file_id: str
    labels: list[str]


class MetadataHistoryEntry(BaseModel):
    file_id: str
    action: str
    detail: str
    actor_email: str
    timestamp: datetime


class MetadataSchemaField(BaseModel):
    name: str
    type: str
    description: str


class MetadataSchemaResponse(BaseModel):
    fields: list[MetadataSchemaField]