"""
Schemas for the Fine-Tuning group of the Model Management APIs
blueprint.
"""

from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, EmailStr, Field

FinetuneStatus = Literal["queued", "running", "completed", "failed", "cancelled"]
FinetuneSource = Literal["trained", "imported"]


# ---------- Shared ----------

class FinetuneHyperparameters(BaseModel):
    epochs: int = Field(3, ge=1, le=50)
    learning_rate: float = Field(1e-5, gt=0)
    batch_size: int = Field(8, ge=1, le=512)


# ---------- Create / job record ----------

class CreateFinetuneJobRequest(BaseModel):
    base_model_id: str
    dataset_id: str
    suffix: Optional[str] = Field(None, max_length=40)
    hyperparameters: FinetuneHyperparameters = Field(default_factory=FinetuneHyperparameters)


class FinetuneJobResponse(BaseModel):
    id: str
    owner_email: EmailStr
    base_model_id: str
    dataset_id: Optional[str] = None
    fine_tuned_model_id: Optional[str] = None
    suffix: Optional[str] = None
    status: FinetuneStatus
    progress_percent: float
    source: FinetuneSource
    hyperparameters: Optional[FinetuneHyperparameters] = None
    created_at: datetime
    updated_at: datetime


class FinetuneJobListResponse(BaseModel):
    total: int
    items: List[FinetuneJobResponse]


# ---------- Cancel ----------

class FinetuneCancelRequest(BaseModel):
    job_id: str


class FinetuneCancelResponse(BaseModel):
    job_id: str
    status: FinetuneStatus
    cancelled_by: str
    cancelled_at: datetime


# ---------- Resume ----------

class FinetuneResumeRequest(BaseModel):
    job_id: str


class FinetuneResumeResponse(BaseModel):
    job_id: str
    status: FinetuneStatus
    resumed_by: str
    resumed_at: datetime


# ---------- Export ----------

class FinetuneExportRequest(BaseModel):
    job_id: str
    format: Literal["safetensors", "gguf", "pytorch"] = "safetensors"


class FinetuneExportResponse(BaseModel):
    job_id: str
    fine_tuned_model_id: str
    export_url: str
    format: str
    exported_at: datetime


# ---------- Import ----------

class FinetuneImportRequest(BaseModel):
    base_model_id: str
    source_url: str
    suffix: Optional[str] = Field(None, max_length=40)


# ---------- Metrics ----------

class FinetuneMetricPoint(BaseModel):
    epoch: int
    step: int
    loss: float
    learning_rate: float


class FinetuneMetricsResponse(BaseModel):
    job_id: str
    status: FinetuneStatus
    metrics: List[FinetuneMetricPoint]
    generated_at: datetime