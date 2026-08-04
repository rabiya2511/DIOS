"""
Schemas for the Datasets group of the Model Management APIs
blueprint.
"""

from datetime import datetime
from typing import Optional, List, Dict, Literal
from pydantic import BaseModel, EmailStr, Field, model_validator

DatasetStatus = Literal["created", "uploaded", "validated", "invalid", "archived"]
DatasetFormat = Literal["jsonl", "csv", "parquet", "text"]
SplitName = Literal["train", "validation", "test"]


# ---------- Create / record ----------

class CreateDatasetRequest(BaseModel):
    name: str
    description: Optional[str] = None
    format: DatasetFormat = "jsonl"
    tags: List[str] = Field(default_factory=list)


class DatasetResponse(BaseModel):
    id: str
    owner_email: EmailStr
    name: str
    description: Optional[str] = None
    format: DatasetFormat
    tags: List[str]
    status: DatasetStatus
    row_count: Optional[int] = None
    size_bytes: Optional[int] = None
    source_url: Optional[str] = None
    parent_dataset_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class DatasetListResponse(BaseModel):
    total: int
    items: List[DatasetResponse]


# ---------- Update ----------

class UpdateDatasetRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None


# ---------- Delete ----------

class DeleteDatasetResponse(BaseModel):
    id: str
    deleted: bool
    deleted_at: datetime


# ---------- Upload ----------

class UploadDatasetRequest(BaseModel):
    dataset_id: str
    source_url: str
    row_count: Optional[int] = Field(None, gt=0)
    size_bytes: Optional[int] = Field(None, gt=0)


class UploadDatasetResponse(BaseModel):
    dataset_id: str
    status: DatasetStatus
    row_count: int
    size_bytes: int
    source_url: str
    uploaded_at: datetime


# ---------- Validate ----------

class ValidationIssue(BaseModel):
    severity: Literal["error", "warning"]
    message: str


class ValidateDatasetRequest(BaseModel):
    dataset_id: str


class ValidateDatasetResponse(BaseModel):
    dataset_id: str
    status: DatasetStatus
    is_valid: bool
    issues: List[ValidationIssue]
    validated_at: datetime


# ---------- Split ----------

class SplitDatasetRequest(BaseModel):
    dataset_id: str
    train_ratio: float = Field(0.8, gt=0, lt=1)
    val_ratio: float = Field(0.1, ge=0, lt=1)
    test_ratio: float = Field(0.1, ge=0, lt=1)

    @model_validator(mode="after")
    def _ratios_sum_to_one(self):
        total = round(self.train_ratio + self.val_ratio + self.test_ratio, 4)
        if total != 1.0:
            raise ValueError(f"train_ratio + val_ratio + test_ratio must sum to 1.0 (got {total})")
        return self


class SplitResult(BaseModel):
    split: SplitName
    dataset_id: str
    row_count: int


class SplitDatasetResponse(BaseModel):
    parent_dataset_id: str
    splits: List[SplitResult]
    created_at: datetime


# ---------- Statistics ----------

class DatasetStatisticsResponse(BaseModel):
    dataset_id: str
    row_count: int
    size_bytes: int
    format: DatasetFormat
    status: DatasetStatus
    class_distribution: Optional[Dict[str, int]] = None
    generated_at: datetime