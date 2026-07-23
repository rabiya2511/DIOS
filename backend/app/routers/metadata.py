"""
Metadata router — tags, labels, classification, history, schema.
Matches the Metadata section of the File & Storage APIs blueprint (8/8).
Mounted at /api/v1/files/metadata.

Only the file owner can view/modify metadata for their own file.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from app.schemas.metadata import (
    MetadataResponse,
    MetadataUpdateRequest,
    TagsAddRequest,
    TagsRemoveRequest,
    ClassifyRequest,
    LabelsAddRequest,
    MetadataHistoryEntry,
    MetadataSchemaField,
    MetadataSchemaResponse,
)
from app.core.security import get_current_user
from app.routers.fileslifecycle import _get_file_or_404, _require_owner

router = APIRouter(prefix="/api/v1/files/metadata", tags=["Metadata"])

# file_id -> {tags: set, labels: set, classification: str|None, custom_fields: dict, updated_at}
file_metadata_db: dict[str, dict] = {}

# append-only history log
metadata_history_db: list[dict] = []

VALID_CLASSIFICATIONS = {"public", "internal", "confidential", "restricted"}


def _get_or_init_metadata(file_id: str) -> dict:
    return file_metadata_db.setdefault(
        file_id,
        {
            "tags": set(),
            "labels": set(),
            "classification": None,
            "custom_fields": {},
            "updated_at": datetime.now(timezone.utc),
        },
    )


def _to_response(file_id: str, meta: dict) -> MetadataResponse:
    return MetadataResponse(
        file_id=file_id,
        tags=sorted(meta["tags"]),
        labels=sorted(meta["labels"]),
        classification=meta["classification"],
        custom_fields=meta["custom_fields"],
        updated_at=meta["updated_at"],
    )


def _log_history(file_id: str, action: str, detail: str, actor_email: str):
    metadata_history_db.append(
        {
            "file_id": file_id,
            "action": action,
            "detail": detail,
            "actor_email": actor_email,
            "timestamp": datetime.now(timezone.utc),
        }
    )


@router.get("", response_model=MetadataResponse)
def get_metadata(
    file_id: str = Query(...),
    current_user: dict = Depends(get_current_user),
):
    file = _get_file_or_404(file_id)
    _require_owner(file, current_user["email"])
    meta = _get_or_init_metadata(file_id)
    return _to_response(file_id, meta)


@router.patch("", response_model=MetadataResponse)
def update_metadata(
    data: MetadataUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    file = _get_file_or_404(data.file_id)
    _require_owner(file, current_user["email"])
    meta = _get_or_init_metadata(data.file_id)
    meta["custom_fields"].update(data.custom_fields)
    meta["updated_at"] = datetime.now(timezone.utc)
    _log_history(data.file_id, "custom_fields_updated", str(data.custom_fields), current_user["email"])
    return _to_response(data.file_id, meta)


@router.post("/tags", response_model=MetadataResponse, status_code=201)
def add_tags(
    data: TagsAddRequest,
    current_user: dict = Depends(get_current_user),
):
    file = _get_file_or_404(data.file_id)
    _require_owner(file, current_user["email"])
    meta = _get_or_init_metadata(data.file_id)
    meta["tags"].update(data.tags)
    meta["updated_at"] = datetime.now(timezone.utc)
    _log_history(data.file_id, "tags_added", ", ".join(data.tags), current_user["email"])
    return _to_response(data.file_id, meta)


@router.delete("/tags", response_model=MetadataResponse)
def remove_tags(
    data: TagsRemoveRequest,
    current_user: dict = Depends(get_current_user),
):
    file = _get_file_or_404(data.file_id)
    _require_owner(file, current_user["email"])
    meta = _get_or_init_metadata(data.file_id)
    meta["tags"].difference_update(data.tags)
    meta["updated_at"] = datetime.now(timezone.utc)
    _log_history(data.file_id, "tags_removed", ", ".join(data.tags), current_user["email"])
    return _to_response(data.file_id, meta)


@router.post("/classify", response_model=MetadataResponse)
def classify_file(
    data: ClassifyRequest,
    current_user: dict = Depends(get_current_user),
):
    if data.classification not in VALID_CLASSIFICATIONS:
        raise HTTPException(
            status_code=422,
            detail=f"classification must be one of {sorted(VALID_CLASSIFICATIONS)}",
        )
    file = _get_file_or_404(data.file_id)
    _require_owner(file, current_user["email"])
    meta = _get_or_init_metadata(data.file_id)
    meta["classification"] = data.classification
    meta["updated_at"] = datetime.now(timezone.utc)
    _log_history(data.file_id, "classified", data.classification, current_user["email"])
    return _to_response(data.file_id, meta)


@router.get("/history", response_model=list[MetadataHistoryEntry])
def get_metadata_history(
    file_id: str = Query(...),
    current_user: dict = Depends(get_current_user),
):
    file = _get_file_or_404(file_id)
    _require_owner(file, current_user["email"])
    return [entry for entry in metadata_history_db if entry["file_id"] == file_id]


@router.post("/labels", response_model=MetadataResponse, status_code=201)
def add_labels(
    data: LabelsAddRequest,
    current_user: dict = Depends(get_current_user),
):
    file = _get_file_or_404(data.file_id)
    _require_owner(file, current_user["email"])
    meta = _get_or_init_metadata(data.file_id)
    meta["labels"].update(data.labels)
    meta["updated_at"] = datetime.now(timezone.utc)
    _log_history(data.file_id, "labels_added", ", ".join(data.labels), current_user["email"])
    return _to_response(data.file_id, meta)


@router.get("/schema", response_model=MetadataSchemaResponse)
def get_metadata_schema():
    """Static description of available metadata fields — no auth required."""
    return MetadataSchemaResponse(
        fields=[
            MetadataSchemaField(name="tags", type="list[string]", description="Freeform tags for search/filtering"),
            MetadataSchemaField(name="labels", type="list[string]", description="Structured labels for categorization"),
            MetadataSchemaField(
                name="classification",
                type="string",
                description=f"One of {sorted(VALID_CLASSIFICATIONS)}",
            ),
            MetadataSchemaField(name="custom_fields", type="object", description="Arbitrary key-value metadata"),
        ]
    )