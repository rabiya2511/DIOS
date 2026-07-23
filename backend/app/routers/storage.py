"""
Storage router — buckets CRUD, usage, quotas, migrate.
Matches the Storage section of the File & Storage APIs blueprint (8/8).
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.storage import (
    BucketCreateRequest,
    BucketUpdateRequest,
    BucketOut,
    StorageUsageOut,
    QuotaOut,
    QuotaUpdateRequest,
    MigrateRequest,
    MigrateResponse,
)
from app.models.user import storage_buckets_db, storage_quotas_db
from app.routers.fileslifecycle import files_db
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/storage", tags=["Storage"])

DEFAULT_QUOTA_BYTES = 5_000_000_000  # 5 GB


def _get_owned_bucket(bucket_id: str, current_user: dict) -> dict:
    bucket = storage_buckets_db.get(bucket_id)
    if not bucket:
        raise HTTPException(status_code=404, detail="Bucket not found")
    if bucket["owner_email"] != current_user["email"]:
        raise HTTPException(status_code=403, detail="Only the bucket owner can perform this action")
    return bucket


@router.get("/buckets", response_model=list[BucketOut])
def list_buckets(current_user: dict = Depends(get_current_user)):
    email = current_user["email"]
    return [b for b in storage_buckets_db.values() if b["owner_email"] == email]


@router.post("/buckets", response_model=BucketOut, status_code=201)
def create_bucket(
    data: BucketCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    bucket_id = str(uuid4())
    bucket = {
        "id": bucket_id,
        "name": data.name,
        "owner_email": current_user["email"],
        "region": data.region,
        "created_at": datetime.now(timezone.utc),
    }
    storage_buckets_db[bucket_id] = bucket
    return bucket


@router.patch("/buckets/{bucket_id}", response_model=BucketOut)
def update_bucket(
    bucket_id: str,
    data: BucketUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    bucket = _get_owned_bucket(bucket_id, current_user)
    if data.name is not None:
        bucket["name"] = data.name
    if data.region is not None:
        bucket["region"] = data.region
    return bucket


@router.delete("/buckets/{bucket_id}", status_code=204)
def delete_bucket(
    bucket_id: str,
    current_user: dict = Depends(get_current_user),
):
    _get_owned_bucket(bucket_id, current_user)
    del storage_buckets_db[bucket_id]
    return None


@router.get("/usage", response_model=StorageUsageOut)
def get_storage_usage(current_user: dict = Depends(get_current_user)):
    email = current_user["email"]
    owned_files = [f for f in files_db.values() if f["owner_email"] == email]
    bucket_count = sum(1 for b in storage_buckets_db.values() if b["owner_email"] == email)
    return StorageUsageOut(
        total_files=len(owned_files),
        total_bytes=sum(f["size_bytes"] for f in owned_files),
        bucket_count=bucket_count,
    )


@router.get("/quotas", response_model=QuotaOut)
def get_quota(current_user: dict = Depends(get_current_user)):
    email = current_user["email"]
    quota = storage_quotas_db.setdefault(
        email, {"limit_bytes": DEFAULT_QUOTA_BYTES, "updated_at": datetime.now(timezone.utc)}
    )
    used = sum(f["size_bytes"] for f in files_db.values() if f["owner_email"] == email)
    return QuotaOut(limit_bytes=quota["limit_bytes"], used_bytes=used)


@router.patch("/quotas", response_model=QuotaOut)
def update_quota(
    data: QuotaUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    email = current_user["email"]
    storage_quotas_db[email] = {"limit_bytes": data.limit_bytes, "updated_at": datetime.now(timezone.utc)}
    used = sum(f["size_bytes"] for f in files_db.values() if f["owner_email"] == email)
    return QuotaOut(limit_bytes=data.limit_bytes, used_bytes=used)


@router.post("/migrate", response_model=MigrateResponse)
def migrate_bucket(
    data: MigrateRequest,
    current_user: dict = Depends(get_current_user),
):
    bucket = _get_owned_bucket(data.bucket_id, current_user)
    bucket["region"] = data.target_region  # simulated — real version would be async and track progress
    now = datetime.now(timezone.utc)
    return MigrateResponse(
        bucket_id=data.bucket_id,
        target_region=data.target_region,
        status="completed",
        started_at=now,
    )