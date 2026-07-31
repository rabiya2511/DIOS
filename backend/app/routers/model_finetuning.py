"""
Router for the Fine-Tuning group of the Model Management APIs
blueprint.
  POST /api/v1/finetune/jobs
  GET  /api/v1/finetune/jobs
  GET  /api/v1/finetune/jobs/{id}
  POST /api/v1/finetune/cancel
  POST /api/v1/finetune/resume
  POST /api/v1/finetune/export
  POST /api/v1/finetune/import
  GET  /api/v1/finetune/metrics

The dynamic route here is /finetune/jobs/{id}, nested one level under
the literal /finetune/jobs path — it doesn't collide with the other
top-level literal routes (/cancel, /resume, /export, /import,
/metrics), so there's no ordering hazard like the /{id}-at-root
pattern in evaluation.py. It's still declared after the plain
GET /finetune/jobs route for readability/consistency.

Jobs are simulated: a job is created in "running" status, and each
time it's fetched (GET /jobs, GET /jobs/{id}) its progress_percent
is advanced by a random increment until it crosses 100%, at which
point it flips to "completed" and gets a fine_tuned_model_id. This
lets you watch a job progress across repeated GET calls without a
real training backend. Swap in a real fine-tuning backend before
relying on this for anything beyond local dev/API-shape testing.

Only the job owner can view/cancel/resume/export their own jobs,
same owner-scoping pattern as evaluation_jobs_db in evaluation.py.
"""

import random
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.schemas.model_finetune import (
    CreateFinetuneJobRequest,
    FinetuneJobResponse,
    FinetuneJobListResponse,
    FinetuneCancelRequest,
    FinetuneCancelResponse,
    FinetuneResumeRequest,
    FinetuneResumeResponse,
    FinetuneExportRequest,
    FinetuneExportResponse,
    FinetuneImportRequest,
    FinetuneMetricPoint,
    FinetuneMetricsResponse,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/finetune", tags=["Fine-Tuning"])

# id -> {id, owner_email, base_model_id, dataset_id, fine_tuned_model_id, suffix,
#        status, progress_percent, source, hyperparameters, created_at, updated_at}
finetune_jobs_db: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _get_job_or_404(job_id: str) -> dict:
    job = finetune_jobs_db.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Fine-tune job not found")
    return job


def _require_owner(job: dict, email: str):
    if job["owner_email"] != email:
        raise HTTPException(status_code=403, detail="Only the fine-tune job owner can perform this action")


def _advance_job(job: dict) -> dict:
    """Simulate training progress: bump percent, flip to completed once it crosses 100."""
    if job["status"] == "running":
        job["progress_percent"] = min(100.0, round(job["progress_percent"] + random.uniform(15, 40), 1))
        job["updated_at"] = datetime.now(timezone.utc)
        if job["progress_percent"] >= 100.0:
            job["status"] = "completed"
            job["progress_percent"] = 100.0
            job["fine_tuned_model_id"] = f"ft:{job['base_model_id']}:{job['id'][:8]}"
    return job


def _simulate_metrics(hyperparameters: dict) -> list[FinetuneMetricPoint]:
    epochs = hyperparameters["epochs"]
    lr = hyperparameters["learning_rate"]
    points = []
    loss = round(random.uniform(1.5, 2.5), 4)
    step = 0
    for epoch in range(1, epochs + 1):
        for _ in range(3):  # 3 simulated steps per epoch
            step += 1
            loss = max(0.05, round(loss - random.uniform(0.05, 0.2), 4))
            points.append(
                FinetuneMetricPoint(epoch=epoch, step=step, loss=loss, learning_rate=lr)
            )
    return points


# ---------------------------------------------------------------------------
# POST /api/v1/finetune/jobs
# ---------------------------------------------------------------------------
@router.post("/jobs", response_model=FinetuneJobResponse, status_code=201)
def create_finetune_job(
    payload: CreateFinetuneJobRequest,
    current_user: dict = Depends(get_current_user),
):
    """Kick off a (simulated) fine-tuning job."""
    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    job = {
        "id": job_id,
        "owner_email": current_user["email"],
        "base_model_id": payload.base_model_id,
        "dataset_id": payload.dataset_id,
        "fine_tuned_model_id": None,
        "suffix": payload.suffix,
        "status": "running",
        "progress_percent": 0.0,
        "source": "trained",
        "hyperparameters": payload.hyperparameters.model_dump(),
        "created_at": now,
        "updated_at": now,
    }
    finetune_jobs_db[job_id] = job
    return job


# ---------------------------------------------------------------------------
# GET /api/v1/finetune/jobs
# ---------------------------------------------------------------------------
@router.get("/jobs", response_model=FinetuneJobListResponse)
def list_finetune_jobs(
    base_model_id: Optional[str] = Query(None),
    status_: Optional[str] = Query(None, alias="status"),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    """List the caller's fine-tune jobs, with optional filters."""
    items = [j for j in finetune_jobs_db.values() if j["owner_email"] == current_user["email"]]

    for job in items:
        _advance_job(job)

    if base_model_id:
        items = [j for j in items if j["base_model_id"] == base_model_id]
    if status_:
        items = [j for j in items if j["status"] == status_]

    items = sorted(items, key=lambda j: j["created_at"], reverse=True)
    total = len(items)
    items = items[offset: offset + limit]
    return FinetuneJobListResponse(total=total, items=items)


# ---------------------------------------------------------------------------
# POST /api/v1/finetune/cancel
# ---------------------------------------------------------------------------
@router.post("/cancel", response_model=FinetuneCancelResponse)
def cancel_finetune_job(
    payload: FinetuneCancelRequest,
    current_user: dict = Depends(get_current_user),
):
    """Cancel a queued or running fine-tune job."""
    job = _get_job_or_404(payload.job_id)
    _require_owner(job, current_user["email"])

    if job["status"] not in ("queued", "running"):
        raise HTTPException(status_code=400, detail=f"Cannot cancel a job in status '{job['status']}'")

    now = datetime.now(timezone.utc)
    job["status"] = "cancelled"
    job["updated_at"] = now

    return FinetuneCancelResponse(
        job_id=payload.job_id, status="cancelled",
        cancelled_by=current_user["email"], cancelled_at=now,
    )


# ---------------------------------------------------------------------------
# POST /api/v1/finetune/resume
# ---------------------------------------------------------------------------
@router.post("/resume", response_model=FinetuneResumeResponse)
def resume_finetune_job(
    payload: FinetuneResumeRequest,
    current_user: dict = Depends(get_current_user),
):
    """Resume a previously cancelled fine-tune job."""
    job = _get_job_or_404(payload.job_id)
    _require_owner(job, current_user["email"])

    if job["status"] != "cancelled":
        raise HTTPException(status_code=400, detail=f"Cannot resume a job in status '{job['status']}'")

    now = datetime.now(timezone.utc)
    job["status"] = "running"
    job["updated_at"] = now

    return FinetuneResumeResponse(
        job_id=payload.job_id, status="running",
        resumed_by=current_user["email"], resumed_at=now,
    )


# ---------------------------------------------------------------------------
# POST /api/v1/finetune/export
# ---------------------------------------------------------------------------
@router.post("/export", response_model=FinetuneExportResponse)
def export_finetune_job(
    payload: FinetuneExportRequest,
    current_user: dict = Depends(get_current_user),
):
    """Export the fine-tuned model artifact for a completed job."""
    job = _get_job_or_404(payload.job_id)
    _require_owner(job, current_user["email"])
    _advance_job(job)

    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"Cannot export a job in status '{job['status']}'")

    now = datetime.now(timezone.utc)
    return FinetuneExportResponse(
        job_id=payload.job_id,
        fine_tuned_model_id=job["fine_tuned_model_id"],
        export_url=f"https://simulated-storage.local/finetune-exports/{job['id']}.{payload.format}",
        format=payload.format,
        exported_at=now,
    )


# ---------------------------------------------------------------------------
# POST /api/v1/finetune/import
# ---------------------------------------------------------------------------
@router.post("/import", response_model=FinetuneJobResponse, status_code=201)
def import_finetune_job(
    payload: FinetuneImportRequest,
    current_user: dict = Depends(get_current_user),
):
    """Register an externally fine-tuned model as a completed job record."""
    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    job = {
        "id": job_id,
        "owner_email": current_user["email"],
        "base_model_id": payload.base_model_id,
        "dataset_id": None,
        "fine_tuned_model_id": f"ft:imported:{job_id[:8]}",
        "suffix": payload.suffix,
        "status": "completed",
        "progress_percent": 100.0,
        "source": "imported",
        "hyperparameters": None,
        "created_at": now,
        "updated_at": now,
    }
    finetune_jobs_db[job_id] = job
    return job


# ---------------------------------------------------------------------------
# GET /api/v1/finetune/metrics
# ---------------------------------------------------------------------------
@router.get("/metrics", response_model=FinetuneMetricsResponse)
def get_finetune_metrics(
    job_id: str = Query(...),
    current_user: dict = Depends(get_current_user),
):
    """Simulated per-step training metrics (loss curve) for a job."""
    job = _get_job_or_404(job_id)
    _require_owner(job, current_user["email"])
    _advance_job(job)

    metrics = (
        _simulate_metrics(job["hyperparameters"])
        if job["status"] in ("running", "completed") and job["source"] == "trained"
        else []
    )

    return FinetuneMetricsResponse(
        job_id=job_id, status=job["status"], metrics=metrics,
        generated_at=datetime.now(timezone.utc),
    )


# ─── Dynamic /jobs/{id} route comes LAST among the /jobs paths ───

@router.get("/jobs/{id}", response_model=FinetuneJobResponse)
def get_finetune_job(id: str, current_user: dict = Depends(get_current_user)):
    """Get a single fine-tune job by id."""
    job = _get_job_or_404(id)
    _require_owner(job, current_user["email"])
    _advance_job(job)
    return job