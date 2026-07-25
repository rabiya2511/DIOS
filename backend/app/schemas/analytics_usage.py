"""
Pydantic schemas for the Analytics: Usage Analytics domain.
"""

from pydantic import BaseModel


class UsersAnalyticsOut(BaseModel):
    total_users: int
    total_admins: int
    total_suspended: int


class ProjectsAnalyticsOut(BaseModel):
    total_projects: int
    active_projects: int
    archived_projects: int


class ModelsAnalyticsOut(BaseModel):
    total_models: int
    total_inferences: int


class TokensAnalyticsOut(BaseModel):
    total_tokens: int
    period: str


class StorageAnalyticsOut(BaseModel):
    total_files: int
    total_bytes: int