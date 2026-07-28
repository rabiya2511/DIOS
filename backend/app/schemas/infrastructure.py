"""
Pydantic schemas for the Infrastructure domain
(Deployment & Infrastructure APIs blueprint).
"""

from datetime import datetime
from typing import Optional, Literal

from pydantic import BaseModel

ClusterStatus = Literal["provisioning", "active", "degraded"]
NodeStatus = Literal["ready", "not_ready"]
ServiceStatus = Literal["healthy", "degraded", "down"]
LoadBalancerStatus = Literal["active", "provisioning"]


class ClusterCreateRequest(BaseModel):
    name: str
    region: str = "us-east-1"
    node_count: int = 3


class ClusterOut(BaseModel):
    id: str
    name: str
    region: str
    status: ClusterStatus
    node_count: int
    created_by: str
    created_at: datetime


class NodeOut(BaseModel):
    id: str
    cluster_id: str
    name: str
    status: NodeStatus
    cpu_cores: int
    memory_gb: int


class ServiceOut(BaseModel):
    id: str
    name: str
    status: ServiceStatus
    replicas: int
    cluster_id: Optional[str] = None


class LoadBalancerOut(BaseModel):
    id: str
    name: str
    status: LoadBalancerStatus
    region: str
    target_service: Optional[str] = None


class StorageVolumeOut(BaseModel):
    id: str
    name: str
    size_gb: int
    region: str
    attached_to: Optional[str] = None