"""
Schemas for the Prompt CRUD domain (Prompt Management APIs blueprint).
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class PromptCreateRequest(BaseModel):
    title: str
    content: str
    tags: list[str] = []


class PromptUpdateRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[list[str]] = None


class PromptResponse(BaseModel):
    id: str
    title: str
    content: str
    tags: list[str] = []
    owner_email: str
    status: str  # "active" | "archived"
    created_at: datetime
    updated_at: datetime


class PromptIdBodyRequest(BaseModel):
    prompt_id: str


class PromptCloneRequest(BaseModel):
    prompt_id: str
    new_title: Optional[str] = None