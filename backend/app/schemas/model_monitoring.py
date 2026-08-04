"""
Pydantic schemas for the Model Monitoring domain (Model Management APIs
blueprint).
"""

from datetime import datetime
from typing import Dict, List

from pydantic import BaseModel


class ModelMetricsResponse(BaseModel):
    total_models: int
    active_count: int
    archived_count: int
    by_provider: Dict[str, int]


class ModelUsageResponse(BaseModel):
    total_requests: int
    total_tokens: int
    by_model: Dict[str, int]


class ModelLatencyResponse(BaseModel):
    avg_latency_ms: float
    by_model: Dict[str, float]


class ModelErrorsResponse(BaseModel):
    total_errors: int
    by_model: Dict[str, int]


class ModelHealthResponse(BaseModel):
    status: str
    total_models_tracked: int
    checked_at: datetime


class ModelCostsResponse(BaseModel):
    total_cost_usd: float
    by_model: Dict[str, float]


class CacheClearResponse(BaseModel):
    cleared_count: int
    cleared_at: datetime


class ModelLogEntry(BaseModel):
    id: str
    model: str
    level: str
    message: str
    timestamp: datetime


class ModelLogsResponse(BaseModel):
    logs: List[ModelLogEntry]