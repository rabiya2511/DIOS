"""
Router for the Datasets group of the Model Management APIs
blueprint.
  GET    /api/v1/datasets
  POST   /api/v1/datasets
  PATCH  /api/v1/datasets/{id}
  DELETE /api/v1/datasets/{id}
  POST   /api/v1/datasets/upload
  POST   /api/v1/datasets/validate
  POST   /api/v1/datasets/split
  GET    /api/v1/datasets/statistics

Literal-path routes (/upload, /validate, /split, /statistics) MUST come
before the dynamic /{id} routes below — same ordering rule as
evaluation.py / conversations.py / fileslifecycle.py. Without this,
a request to e.g. POST /datasets/upload would be matched by the
PATCH/DELETE /datasets/{id} route with id="upload" instead (FastAPI
matches routes in declaration order).

All data here is simulated — uploads don't touch real storage,
validation issues are randomly generated, and splits just derive
child row counts from the parent's row_count. Swap in a real storage/
validation backend before relying on this for anything beyond local
dev/API-shape testing.

Only the dataset's owner can update/delete/upload/validate/split it,
same owner-scoping pattern as evaluation_jobs_db in evaluation.py.
"""

import random
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.schemas.model_dataset import (
    CreateDatasetRequest,
    DatasetResponse,
    DatasetListResponse,
    UpdateDatasetRequest,
    DeleteDatasetResponse,
    UploadDatasetRequest,
    UploadDatasetResponse,
    ValidateDatasetRequest,
    ValidateDatasetResponse,
    ValidationIssue,
    SplitDatasetRequest,
    SplitDatasetResponse,
    SplitResult,
    DatasetStatisticsResponse,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/datasets", tags=["Datasets"])

# id -> dataset dict
# {id, owner_email, name, description, format, tags, status, row_count,
#  size_bytes, source_url, parent_dataset_id, created_at, updated_at}
datasets_db: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _get_dataset_or_404(dataset_id: str) -> dict:
    dataset = datasets_db.get(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


def _require_owner(dataset: dict, email: str):
    if dataset["owner_email"] != email:
        raise HTTPException(status_code=403, detail="Only the dataset owner can perform this action")


def _simulate_validation_issues() -> list[ValidationIssue]:
    pool = [
        ValidationIssue(severity="warning", message="A small number of rows have empty fields"),
        ValidationIssue(severity="warning", message="Duplicate rows detected"),
        ValidationIssue(severity="error", message="Schema mismatch on some rows"),
    ]
    return random.sample(pool, k=random.randint(0, 2))


# ---------------------------------------------------------------------------
# POST /api/v1/datasets
# ---------------------------------------------------------------------------
@router.post("", response_model=DatasetResponse, status_code=201)
def create_dataset(
    payload: CreateDatasetRequest,
    current_user: dict = Depends(get_current_user),
):
    """Create a new dataset record (metadata only, no data uploaded yet)."""
    dataset_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    dataset = {
        "id": dataset_id,
        "owner_email": current_user["email"],
        "name": payload.name,
        "description": payload.description,
        "format": payload.format,
        "tags": payload.tags,
        "status": "created",
        "row_count": None,
        "size_bytes": None,
        "source_url": None,
        "parent_dataset_id": None,
        "created_at": now,
        "updated_at": now,
    }
    datasets_db[dataset_id] = dataset
    return dataset


# ---------------------------------------------------------------------------
# GET /api/v1/datasets
# ---------------------------------------------------------------------------
@router.get("", response_model=DatasetListResponse)
def list_datasets(
    status_: Optional[str] = Query(None, alias="status"),
    format_: Optional[str] = Query(None, alias="format"),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    """List the caller's datasets, with optional filters."""
    items = [d for d in datasets_db.values() if d["owner_email"] == current_user["email"]]

    if status_:
        items = [d for d in items if d["status"] == status_]
    if format_:
        items = [d for d in items if d["format"] == format_]

    items = sorted(items, key=lambda d: d["created_at"], reverse=True)
    total = len(items)
    items = items[offset: offset + limit]
    return DatasetListResponse(total=total, items=items)


# ---------------------------------------------------------------------------
# POST /api/v1/datasets/upload
# ---------------------------------------------------------------------------
@router.post("/upload", response_model=UploadDatasetResponse)
def upload_dataset(
    payload: UploadDatasetRequest,
    current_user: dict = Depends(get_current_user),
):
    """Simulate uploading data into an existing dataset record."""
    dataset = _get_dataset_or_404(payload.dataset_id)
    _require_owner(dataset, current_user["email"])

    now = datetime.now(timezone.utc)
    row_count = payload.row_count or random.randint(500, 50_000)
    size_bytes = payload.size_bytes or row_count * random.randint(80, 400)

    dataset["status"] = "uploaded"
    dataset["row_count"] = row_count
    dataset["size_bytes"] = size_bytes
    dataset["source_url"] = payload.source_url
    dataset["updated_at"] = now

    return UploadDatasetResponse(
        dataset_id=dataset["id"], status=dataset["status"],
        row_count=row_count, size_bytes=size_bytes,
        source_url=payload.source_url, uploaded_at=now,
    )


# ---------------------------------------------------------------------------
# POST /api/v1/datasets/validate
# ---------------------------------------------------------------------------
@router.post("/validate", response_model=ValidateDatasetResponse)
def validate_dataset(
    payload: ValidateDatasetRequest,
    current_user: dict = Depends(get_current_user),
):
    """Simulate validating an uploaded dataset."""
    dataset = _get_dataset_or_404(payload.dataset_id)
    _require_owner(dataset, current_user["email"])

    if dataset["row_count"] is None:
        raise HTTPException(status_code=400, detail="Cannot validate a dataset with no uploaded data")

    now = datetime.now(timezone.utc)
    issues = _simulate_validation_issues()
    is_valid = not any(i.severity == "error" for i in issues)

    dataset["status"] = "validated" if is_valid else "invalid"
    dataset["updated_at"] = now

    return ValidateDatasetResponse(
        dataset_id=dataset["id"], status=dataset["status"],
        is_valid=is_valid, issues=issues, validated_at=now,
    )


# ---------------------------------------------------------------------------
# POST /api/v1/datasets/split
# ---------------------------------------------------------------------------
@router.post("/split", response_model=SplitDatasetResponse)
def split_dataset(
    payload: SplitDatasetRequest,
    current_user: dict = Depends(get_current_user),
):
    """Split a dataset into train/validation/test child dataset records."""
    parent = _get_dataset_or_404(payload.dataset_id)
    _require_owner(parent, current_user["email"])

    if parent["row_count"] is None:
        raise HTTPException(status_code=400, detail="Cannot split a dataset with no uploaded data")

    now = datetime.now(timezone.utc)
    ratios = {
        "train": payload.train_ratio,
        "validation": payload.val_ratio,
        "test": payload.test_ratio,
    }

    splits = []
    for split_name, ratio in ratios.items():
        if ratio <= 0:
            continue
        child_id = str(uuid.uuid4())
        child_row_count = round(parent["row_count"] * ratio)
        datasets_db[child_id] = {
            "id": child_id,
            "owner_email": current_user["email"],
            "name": f"{parent['name']}-{split_name}",
            "description": parent["description"],
            "format": parent["format"],
            "tags": parent["tags"],
            "status": "uploaded",
            "row_count": child_row_count,
            "size_bytes": round((parent["size_bytes"] or 0) * ratio),
            "source_url": parent["source_url"],
            "parent_dataset_id": parent["id"],
            "created_at": now,
            "updated_at": now,
        }
        splits.append(SplitResult(split=split_name, dataset_id=child_id, row_count=child_row_count))

    return SplitDatasetResponse(parent_dataset_id=parent["id"], splits=splits, created_at=now)


# ---------------------------------------------------------------------------
# GET /api/v1/datasets/statistics
# ---------------------------------------------------------------------------
@router.get("/statistics", response_model=DatasetStatisticsResponse)
def get_dataset_statistics(
    dataset_id: str = Query(...),
    current_user: dict = Depends(get_current_user),
):
    """Simulated statistics for an uploaded dataset."""
    dataset = _get_dataset_or_404(dataset_id)
    _require_owner(dataset, current_user["email"])

    if dataset["row_count"] is None:
        raise HTTPException(status_code=400, detail="Cannot compute statistics for a dataset with no uploaded data")

    class_distribution = None
    if dataset["format"] in ("jsonl", "csv"):
        remaining = dataset["row_count"]
        labels = ["positive", "negative", "neutral"]
        class_distribution = {}
        for label in labels[:-1]:
            count = random.randint(0, remaining)
            class_distribution[label] = count
            remaining -= count
        class_distribution[labels[-1]] = remaining

    return DatasetStatisticsResponse(
        dataset_id=dataset["id"], row_count=dataset["row_count"],
        size_bytes=dataset["size_bytes"] or 0, format=dataset["format"],
        status=dataset["status"], class_distribution=class_distribution,
        generated_at=datetime.now(timezone.utc),
    )


# ─── Dynamic /{id} routes come LAST ───

@router.patch("/{id}", response_model=DatasetResponse)
def update_dataset(
    id: str,
    payload: UpdateDatasetRequest,
    current_user: dict = Depends(get_current_user),
):
    """Update a dataset's metadata (name, description, tags)."""
    dataset = _get_dataset_or_404(id)
    _require_owner(dataset, current_user["email"])

    if payload.name is not None:
        dataset["name"] = payload.name
    if payload.description is not None:
        dataset["description"] = payload.description
    if payload.tags is not None:
        dataset["tags"] = payload.tags

    dataset["updated_at"] = datetime.now(timezone.utc)
    return dataset


@router.delete("/{id}", response_model=DeleteDatasetResponse)
def delete_dataset(id: str, current_user: dict = Depends(get_current_user)):
    """Delete a dataset record."""
    dataset = _get_dataset_or_404(id)
    _require_owner(dataset, current_user["email"])

    del datasets_db[id]
    return DeleteDatasetResponse(id=id, deleted=True, deleted_at=datetime.now(timezone.utc))