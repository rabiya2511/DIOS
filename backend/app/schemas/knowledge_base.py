"""
Pydantic schemas for the Knowledge / RAG: Knowledge Base domain.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class KnowledgeCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None


class KnowledgeUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class KnowledgeOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    owner_email: str
    status: str
    created_at: datetime
    updated_at: datetime


class KnowledgeIdBodyRequest(BaseModel):
    knowledge_id: str


class KnowledgeCloneRequest(BaseModel):
    knowledge_id: str
    new_name: Optional[str] = None