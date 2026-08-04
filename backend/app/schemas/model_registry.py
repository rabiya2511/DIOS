"""
Pydantic schemas for the Model Registry domain (Model Management APIs
blueprint).
"""

from datetime import datetime
from typing import Optional, Literal

from pydantic import BaseModel

ModelStatus = Literal["active", "archived"]
ModelSource = Literal["created", "registered"]


class ModelCreateRequest(BaseModel):
    name: str
    provider: str = "custom"
    base_model: Optional[str] = None


class ModelRegisterRequest(BaseModel):
    name: str
    provider: str
    external_id: str


class ModelUpdateRequest(BaseModel):
    name: Optional[str] = None
    provider: Optional[str] = None
    base_model: Optional[str] = None


class ModelOut(BaseModel):
    id: str
    name: str
    provider: str
    base_model: Optional[str] = None
    external_id: Optional[str] = None
    source: ModelSource
    status: ModelStatus
    owner_email: str
    created_at: datetime
    updated_at: datetime


class ModelIdBodyRequest(BaseModel):
    model_id: str