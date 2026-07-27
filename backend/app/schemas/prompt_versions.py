"""
Pydantic schemas for the Versioning domain (Prompt Management APIs
blueprint). Versions are snapshots of a prompt's title/content/tags at
a point in time; promote/rollback write a chosen version back onto the
live prompt in prompts_db.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class VersionResponse(BaseModel):
    version: int
    title: str
    content: str
    tags: list[str]
    created_at: datetime


class VersionCreateRequest(BaseModel):
    # optional overrides — if omitted, snapshots the prompt's current live state
    title: str | None = None
    content: str | None = None
    tags: list[str] | None = None


class VersionUpdateRequest(BaseModel):
    title: str | None = None
    content: str | None = None
    tags: list[str] | None = None


class VersionActionRequest(BaseModel):
    version: int


class HistoryEntry(BaseModel):
    prompt_id: str
    action: Literal["version_created", "version_updated", "version_deleted", "promoted", "rolled_back"]
    version: int | None = None
    timestamp: datetime


class CompareRequest(BaseModel):
    version_a: int
    version_b: int


class CompareResponse(BaseModel):
    version_a: int
    version_b: int
    title_changed: bool
    content_changed: bool
    tags_changed: bool