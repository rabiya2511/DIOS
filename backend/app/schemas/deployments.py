"""
Pydantic schemas for the Deployment Management domain
(Deployment & Infrastructure APIs blueprint).
"""

from datetime import datetime
from typing import Optional, Literal

from pydantic import BaseModel

DeploymentStatus = Literal["active", "rolled_back", "failed"]
HistoryAction = Literal["created", "updated", "rolled_back"]


class DeploymentCreateRequest(BaseModel):
    name: str
    version: str
    environment: str = "production"


class DeploymentUpdateRequest(BaseModel):
    name: Optional[str] = None
    version: Optional[str] = None
    environment: Optional[str] = None


class DeploymentOut(BaseModel):
    id: str
    name: str
    version: str
    environment: str
    status: DeploymentStatus
    owner_email: str
    created_at: datetime
    updated_at: datetime


class DeploymentRollbackRequest(BaseModel):
    deployment_id: str
    target_version: Optional[str] = None


class DeploymentHistoryEntry(BaseModel):
    id: str
    deployment_id: str
    action: HistoryAction
    version: str
    timestamp: datetime