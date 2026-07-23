"""
Schemas for Folders domain.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class FolderCreateRequest(BaseModel):
    name: str
    parent_folder_id: Optional[str] = None


class FolderUpdateRequest(BaseModel):
    name: Optional[str] = None
    parent_folder_id: Optional[str] = None


class FolderResponse(BaseModel):
    id: str
    name: str
    parent_folder_id: Optional[str] = None
    owner_email: str
    status: str  # "active" | "archived"
    created_at: datetime
    updated_at: datetime


class FolderIdBodyRequest(BaseModel):
    folder_id: str


class FolderShareRequest(BaseModel):
    folder_id: str
    email: str


class FolderShareResponse(BaseModel):
    folder_id: str
    shared_with_email: str
    shared_at: datetime


class FolderTreeNode(BaseModel):
    id: str
    name: str
    children: list["FolderTreeNode"] = []


FolderTreeNode.model_rebuild()