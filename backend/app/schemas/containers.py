"""
Pydantic schemas for the Containers & Images domain
(Deployment & Infrastructure APIs blueprint).
"""

from datetime import datetime
from typing import List, Optional, Literal

from pydantic import BaseModel

ContainerStatus = Literal["running", "stopped", "crashed"]
ImageStatus = Literal["built", "pushed"]


class ContainerOut(BaseModel):
    id: str
    name: str
    image: str
    status: ContainerStatus
    cluster_id: Optional[str] = None


class ImageBuildRequest(BaseModel):
    name: str
    tag: str = "latest"
    source_ref: Optional[str] = None


class ImagePushRequest(BaseModel):
    image_id: str
    registry: str = "docker.io"


class ImageScanRequest(BaseModel):
    image_id: str


class ImageOut(BaseModel):
    id: str
    name: str
    tag: str
    size_mb: int
    status: ImageStatus
    pushed_to_registry: bool
    registry: Optional[str] = None
    vulnerabilities: Optional[List[str]] = None
    last_scanned_at: Optional[datetime] = None
    built_by: str
    created_at: datetime