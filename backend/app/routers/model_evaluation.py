"""
Router for the Evaluation group of the Model Management APIs
blueprint.
  POST /api/v1/evaluation/run
  GET  /api/v1/evaluation/jobs
  GET  /api/v1/evaluation/{id}
  POST /api/v1/evaluation/benchmark
  POST /api/v1/evaluation/compare
  GET  /api/v1/evaluation/reports
  POST /api/v1/evaluation/approve
  POST /api/v1/evaluation/reject

Literal-path routes (/run, /jobs, /benchmark, /compare, /reports,
/approve, /reject) MUST come before the dynamic /{id} route below —
same ordering rule as conversations.py / fileslifecycle.py.

Only the evaluation job's owner can approve/reject it. Uses local
in-memory dicts (same pattern as conversations_db in conversations.py).

Evaluation runs and benchmarks are simulated — metrics are randomly
generated, not computed from a real model/dataset. Swap in a real
evaluation harness before relying on this for anything beyond local
dev/API-shape testing.
"""

import random
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.schemas.model_evaluation import (
    EvaluationRunRequest,
    EvaluationJobResponse,
    EvaluationJobListResponse,
    BenchmarkRequest,
    BenchmarkResponse,
    CompareRequest,
    CompareResponse,
    EvaluationReportEntry,
    EvaluationReportsResponse,
    EvaluationApproveRequest,
    EvaluationApproveResponse,
    EvaluationRejectRequest,
    EvaluationRejectResponse,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/evaluation", tags=["Model Evaluation"])

# id -> {id, owner_email, model_id, dataset_id, status, metrics, config, created_at, updated_at}
evaluation_jobs_db: dict[str, dict] = {}
# id -> {id, benchmark_name, model_ids, results, status, created_at}
benchmarks_db: dict[str, dict] = {}


def _simulate_metrics() -> dict:
    return {
        "accuracy": round(random.uniform(0.75, 0.98), 4),
        "avg_latency_ms": round(random.uniform(80, 400), 1),
    }


def _get_job_or_404(evaluation_id: str) -> dict:
    job = evaluation_jobs_db.get(evaluation_id)
    if not job:
        raise HTTPException(status_code=404, detail="Evaluation job not found")
    return job


def _require_owner(job: dict, email: str):
    if job["owner_email"] != email:
        raise HTTPException(status_code=403, detail="Only the evaluation owner can perform this action")


# ---------------------------------------------------------------------------
# POST /api/v1/evaluation/run
# ---------------------------------------------------------------------------
@router.post("/run", response_model=EvaluationJobResponse, status_code=201)
def run_evaluation(
    payload: EvaluationRunRequest,
    current_user: dict = Depends(get_current_user),
):
    """Run a (simulated) evaluation job for a model against a dataset."""
    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    job = {
        "id": job_id,
        "owner_email": current_user["email"],
        "model_id": payload.model_id,
        "dataset_id": payload.dataset_id,
        "status": "completed",
        "metrics": _simulate_metrics(),
        "config": payload.config,
        "created_at": now,
        "updated_at": now,
    }
    evaluation_jobs_db[job_id] = job
    return job


# ---------------------------------------------------------------------------
# GET /api/v1/evaluation/jobs
# ---------------------------------------------------------------------------
@router.get("/jobs", response_model=EvaluationJobListResponse)
def list_evaluation_jobs(
    model_id: Optional[str] = Query(None),
    status_: Optional[str] = Query(None, alias="status"),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    """List the caller's evaluation jobs, with optional filters."""
    items = [j for j in evaluation_jobs_db.values() if j["owner_email"] == current_user["email"]]

    if model_id:
        items = [j for j in items if j["model_id"] == model_id]
    if status_:
        items = [j for j in items if j["status"] == status_]

    items = sorted(items, key=lambda j: j["created_at"], reverse=True)
    total = len(items)
    items = items[offset: offset + limit]
    return EvaluationJobListResponse(total=total, items=items)


# ---------------------------------------------------------------------------
# POST /api/v1/evaluation/benchmark
# ---------------------------------------------------------------------------
@router.post("/benchmark", response_model=BenchmarkResponse, status_code=201)
def run_benchmark(
    payload: BenchmarkRequest,
    current_user: dict = Depends(get_current_user),
):
    """Run a (simulated) benchmark across multiple models."""
    benchmark_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    results = {model_id: _simulate_metrics() for model_id in payload.model_ids}

    benchmarks_db[benchmark_id] = {
        "id": benchmark_id, "benchmark_name": payload.benchmark_name,
        "model_ids": payload.model_ids, "results": results,
        "status": "completed", "created_at": now,
    }
    return BenchmarkResponse(
        id=benchmark_id, benchmark_name=payload.benchmark_name,
        model_ids=payload.model_ids, results=results, status="completed", created_at=now,
    )


# ---------------------------------------------------------------------------
# POST /api/v1/evaluation/compare
# ---------------------------------------------------------------------------
@router.post("/compare", response_model=CompareResponse)
def compare_evaluations(
    payload: CompareRequest,
    current_user: dict = Depends(get_current_user),
):
    """Compare metrics across two or more completed evaluation jobs."""
    jobs = []
    for evaluation_id in payload.evaluation_ids:
        job = _get_job_or_404(evaluation_id)
        if job["owner_email"] != current_user["email"]:
            raise HTTPException(status_code=403, detail=f"Not authorized to compare evaluation {evaluation_id}")
        if not job["metrics"]:
            raise HTTPException(status_code=400, detail=f"Evaluation {evaluation_id} has no metrics to compare")
        jobs.append(job)

    all_metric_names = sorted({m for job in jobs for m in job["metrics"].keys()})
    comparison = {
        metric: {job["id"]: job["metrics"].get(metric) for job in jobs}
        for metric in all_metric_names
    }

    return CompareResponse(
        evaluation_ids=payload.evaluation_ids, comparison=comparison,
        generated_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# GET /api/v1/evaluation/reports
# ---------------------------------------------------------------------------
@router.get("/reports", response_model=EvaluationReportsResponse)
def get_evaluation_reports(
    current_user: dict = Depends(get_current_user),
):
    """Summary report entries for all of the caller's evaluation jobs."""
    now = datetime.now(timezone.utc)
    owned = [j for j in evaluation_jobs_db.values() if j["owner_email"] == current_user["email"]]

    items = [
        EvaluationReportEntry(
            id=job["id"], model_id=job["model_id"], status=job["status"],
            summary=(
                f"Accuracy {job['metrics']['accuracy']:.2%}" if job.get("metrics") else "No metrics yet"
            ),
            generated_at=now,
        )
        for job in sorted(owned, key=lambda j: j["created_at"], reverse=True)
    ]
    return EvaluationReportsResponse(total=len(items), items=items)


# ---------------------------------------------------------------------------
# POST /api/v1/evaluation/approve
# ---------------------------------------------------------------------------
@router.post("/approve", response_model=EvaluationApproveResponse)
def approve_evaluation(
    payload: EvaluationApproveRequest,
    current_user: dict = Depends(get_current_user),
):
    """Approve a completed evaluation job (e.g. to greenlight promotion/deployment)."""
    job = _get_job_or_404(payload.evaluation_id)
    _require_owner(job, current_user["email"])

    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"Cannot approve an evaluation in status '{job['status']}'")

    now = datetime.now(timezone.utc)
    job["status"] = "approved"
    job["updated_at"] = now

    return EvaluationApproveResponse(
        evaluation_id=payload.evaluation_id, status="approved",
        approved_by=current_user["email"], approved_at=now,
    )


# ---------------------------------------------------------------------------
# POST /api/v1/evaluation/reject
# ---------------------------------------------------------------------------
@router.post("/reject", response_model=EvaluationRejectResponse)
def reject_evaluation(
    payload: EvaluationRejectRequest,
    current_user: dict = Depends(get_current_user),
):
    """Reject a completed evaluation job."""
    job = _get_job_or_404(payload.evaluation_id)
    _require_owner(job, current_user["email"])

    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"Cannot reject an evaluation in status '{job['status']}'")

    now = datetime.now(timezone.utc)
    job["status"] = "rejected"
    job["updated_at"] = now

    return EvaluationRejectResponse(
        evaluation_id=payload.evaluation_id, status="rejected",
        rejected_by=current_user["email"], rejected_at=now, reason=payload.reason,
    )


# ─── Dynamic /{id} route comes LAST ───

@router.get("/{id}", response_model=EvaluationJobResponse)
def get_evaluation(id: str, current_user: dict = Depends(get_current_user)):
    """Get a single evaluation job by id."""
    job = _get_job_or_404(id)
    _require_owner(job, current_user["email"])
    return job