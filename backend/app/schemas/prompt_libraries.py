"""
Pydantic schemas for the Prompt Libraries & Sharing domain
(Prompt Management APIs blueprint).
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr


class PromptLibraryPublishRequest(BaseModel):
    prompt_id: str
    title: Optional[str] = None


class PromptLibraryEntryOut(BaseModel):
    id: str
    prompt_id: str
    title: str
    content: str
    tags: List[str]
    published_by: EmailStr
    created_at: datetime


class PromptShareRequest(BaseModel):
    prompt_id: str
    email: EmailStr


class PromptShareResponse(BaseModel):
    prompt_id: str
    shared_with: List[EmailStr]


class PromptFavoriteRequest(BaseModel):
    prompt_id: str


class PromptFavoriteResponse(BaseModel):
    prompt_id: str
    favorited: bool


class PromptTagsResponse(BaseModel):
    tags: List[str]


class PromptTagsAddRequest(BaseModel):
    prompt_id: str
    tags: List[str]


class PromptTagsAddResponse(BaseModel):
    prompt_id: str
    tags: List[str]