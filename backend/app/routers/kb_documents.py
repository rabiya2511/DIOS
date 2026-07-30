"""
Documents router — upload, list, get, update, delete, bulk-upload,
export, import.
Matches the Documents section of the Knowledge / RAG APIs blueprint
(8/8). Only the document owner can update/delete/export their own
document.

*** ROUTING NOTE ***
/documents/bulk-upload, /documents/export, /documents/import are
literal paths under /api/v1/documents, the same shape as this
router's own dynamic GET/PATCH/DELETE /documents/{id}. All literal
routes are registered BEFORE the /{id} routes below.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.kb_documents import (
    DocumentUploadRequest,
    DocumentUpdateRequest,
    DocumentOut,
    BulkUploadRequest,
    DocumentExportRequest,
    DocumentImportRequest,
)
from app.models.user import kb_documents_db
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/documents", tags=["Knowledge / RAG: Documents"])


def _get_doc_or_404(id: str) -> dict:
    doc = kb_documents_db.get(id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


def _require_owner(doc: dict, email: str):
    if doc["owner_email"] != email:
        raise HTTPException(status_code=403, detail="Only the document owner can perform this action")


def _create_doc(data: DocumentUploadRequest, owner_email: str) -> dict:
    doc_id = str(uuid4())
    now = datetime.now(timezone.utc)
    doc = {
        "id": doc_id,
        "knowledge_id": data.knowledge_id,
        "title": data.title,
        "content": data.content,
        "owner_email": owner_email,
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }
    kb_documents_db[doc_id] = doc
    return doc


@router.post("/upload", response_model=DocumentOut, status_code=201)
def upload_document(
    data: DocumentUploadRequest,
    current_user: dict = Depends(get_current_user),
):
    return _create_doc(data, current_user["email"])


@router.get("", response_model=list[DocumentOut])
def list_documents(current_user: dict = Depends(get_current_user)):
    return [d for d in kb_documents_db.values() if d["owner_email"] == current_user["email"]]


# ─── Literal-path routes MUST come before any /{id} routes below ───

@router.post("/bulk-upload", response_model=list[DocumentOut], status_code=201)
def bulk_upload_documents(
    data: BulkUploadRequest,
    current_user: dict = Depends(get_current_user),
):
    uploaded = []
    for item in data.documents:
        if item.knowledge_id is None:
            item.knowledge_id = data.knowledge_id
        uploaded.append(_create_doc(item, current_user["email"]))
    return uploaded


@router.post("/export", response_model=DocumentOut)
def export_document(
    data: DocumentExportRequest,
    current_user: dict = Depends(get_current_user),
):
    doc = _get_doc_or_404(data.document_id)
    _require_owner(doc, current_user["email"])
    return doc


@router.post("/import", response_model=DocumentOut, status_code=201)
def import_document(
    data: DocumentImportRequest,
    current_user: dict = Depends(get_current_user),
):
    upload_data = DocumentUploadRequest(
        knowledge_id=data.knowledge_id, title=data.title, content=data.content
    )
    return _create_doc(upload_data, current_user["email"])


# ─── Dynamic /{id} routes come LAST ───

@router.get("/{id}", response_model=DocumentOut)
def get_document(id: str, current_user: dict = Depends(get_current_user)):
    doc = _get_doc_or_404(id)
    _require_owner(doc, current_user["email"])
    return doc


@router.patch("/{id}", response_model=DocumentOut)
def update_document(
    id: str,
    data: DocumentUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    doc = _get_doc_or_404(id)
    _require_owner(doc, current_user["email"])
    if data.title is not None:
        doc["title"] = data.title
    if data.content is not None:
        doc["content"] = data.content
    doc["updated_at"] = datetime.now(timezone.utc)
    return doc


@router.delete("/{id}", status_code=204)
def delete_document(id: str, current_user: dict = Depends(get_current_user)):
    doc = _get_doc_or_404(id)
    _require_owner(doc, current_user["email"])
    del kb_documents_db[id]
    return None