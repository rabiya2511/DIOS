"""
Pydantic schemas for the Model Versions domain (Model Management APIs
blueprint). Builds on models_db from model_registry.py.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ModelVersionResponse(BaseModel):
    version: int
    name: str
    provider: str
    base_model: str | None = None
    created_at: datetime


class ModelVersionCreateRequest(BaseModel):
    # optional overrides — if omitted, snapshots the model's current live state
    name: str | None = None
    provider: str | None = None
    base_model: str | None = None


class ModelVersionUpdateRequest(BaseModel):
    name: str | None = None
    provider: str | None = None
    base_model: str | None = None


class ModelVersionActionRequest(BaseModel):
    version: int


class ModelChangelogEntry(BaseModel):
    model_id: str
    action: Literal["version_created", "version_updated", "version_deleted", "promoted", "rolled_back", "cloned"]
    version: int | None = None
    timestamp: datetime


class ModelCloneRequest(BaseModel):
    new_name: str | None = None