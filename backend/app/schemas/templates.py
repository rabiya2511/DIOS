"""
Schemas for the Templates domain (Prompt Management APIs blueprint).
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class TemplateCreateRequest(BaseModel):
    name: str
    content: str
    variables: list[str] = []  # e.g. ["customer_name", "product"]


class TemplateUpdateRequest(BaseModel):
    name: Optional[str] = None
    content: Optional[str] = None
    variables: Optional[list[str]] = None


class TemplateResponse(BaseModel):
    id: str
    name: str
    content: str
    variables: list[str] = []
    owner_email: str
    created_at: datetime
    updated_at: datetime


class TemplateImportItem(BaseModel):
    name: str
    content: str
    variables: list[str] = []


class TemplateImportRequest(BaseModel):
    templates: list[TemplateImportItem]


class TemplateImportResponse(BaseModel):
    imported_count: int


class TemplateDuplicateRequest(BaseModel):
    template_id: str
    new_name: Optional[str] = None