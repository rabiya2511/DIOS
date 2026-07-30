"""
Pydantic schemas for the Knowledge / RAG: Documents domain.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DocumentUploadRequest(BaseModel):
    knowledge_id: Optional[str] = None
    title: str
    content: str


class DocumentUpdateRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None


class DocumentOut(BaseModel):
    id: str
    knowledge_id: Optional[str] = None
    title: str
    content: str
    owner_email: str
    status: str
    created_at: datetime
    updated_at: datetime


class BulkUploadRequest(BaseModel):
    knowledge_id: Optional[str] = None
    documents: list[DocumentUploadRequest]


class DocumentExportRequest(BaseModel):
    document_id: str


class DocumentImportRequest(BaseModel):
    knowledge_id: Optional[str] = None
    title: str
    content: str