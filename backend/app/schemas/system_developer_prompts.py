"""
Schemas for the System & Developer Prompts domain
(Prompt Management APIs blueprint).
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SystemPromptCreateRequest(BaseModel):
    content: str
    description: Optional[str] = None


class SystemPromptUpdateRequest(BaseModel):
    content: Optional[str] = None
    description: Optional[str] = None


class SystemPromptResponse(BaseModel):
    id: str
    content: str
    description: Optional[str] = None
    owner_email: str
    created_at: datetime
    updated_at: datetime


class DeveloperPromptCreateRequest(BaseModel):
    content: str
    description: Optional[str] = None


class DeveloperPromptUpdateRequest(BaseModel):
    content: Optional[str] = None
    description: Optional[str] = None


class DeveloperPromptResponse(BaseModel):
    id: str
    content: str
    description: Optional[str] = None
    owner_email: str
    created_at: datetime
    updated_at: datetime