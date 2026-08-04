"""
Schemas for the Evaluation group of the Model Management APIs
blueprint.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, EmailStr, Field

EvaluationStatus = Literal["pending", "running", "completed", "failed", "approved", "rejected"]


# ---------- Run ----------

class EvaluationRunRequest(BaseModel):
    model_id: str
    dataset_id: Optional[str] = None
    config: Dict[str, Any] = Field(default_factory=dict, description="e.g. task type, metrics to compute")


class EvaluationJobResponse(BaseModel):
    id: str
    owner_email: EmailStr
    model_id: str
    dataset_id: Optional[str] = None
    status: EvaluationStatus
    metrics: Optional[Dict[str, float]] = None
    config: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class EvaluationJobListResponse(BaseModel):
    total: int
    items: List[EvaluationJobResponse]


# ---------- Benchmark ----------

class BenchmarkRequest(BaseModel):
    model_ids: List[str] = Field(..., min_length=1)
    benchmark_name: str
    config: Dict[str, Any] = Field(default_factory=dict)


class BenchmarkResponse(BaseModel):
    id: str
    benchmark_name: str
    model_ids: List[str]
    results: Dict[str, Dict[str, float]] = Field(..., description="model_id -> {metric: score}")
    status: str
    created_at: datetime


# ---------- Compare ----------

class CompareRequest(BaseModel):
    evaluation_ids: List[str] = Field(..., min_length=2)


class CompareResponse(BaseModel):
    evaluation_ids: List[str]
    comparison: Dict[str, Dict[str, float]] = Field(..., description="metric -> {evaluation_id: value}")
    generated_at: datetime


# ---------- Reports ----------

class EvaluationReportEntry(BaseModel):
    id: str
    model_id: str
    status: EvaluationStatus
    summary: str
    generated_at: datetime


class EvaluationReportsResponse(BaseModel):
    total: int
    items: List[EvaluationReportEntry]


# ---------- Approve / Reject ----------

class EvaluationApproveRequest(BaseModel):
    evaluation_id: str


class EvaluationApproveResponse(BaseModel):
    evaluation_id: str
    status: EvaluationStatus
    approved_by: str
    approved_at: datetime


class EvaluationRejectRequest(BaseModel):
    evaluation_id: str
    reason: Optional[str] = None


class EvaluationRejectResponse(BaseModel):
    evaluation_id: str
    status: EvaluationStatus
    rejected_by: str
    rejected_at: datetime
    reason: Optional[str] = None