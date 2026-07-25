"""
Analytics router — Usage Analytics.
Matches the Usage Analytics section of the Analytics APIs blueprint (5/5).
"""

from fastapi import APIRouter, Depends

from app.schemas.analytics_usage import (
    UsersAnalyticsOut,
    ProjectsAnalyticsOut,
    ModelsAnalyticsOut,
    TokensAnalyticsOut,
    StorageAnalyticsOut,
)
from app.models.user import users_db, audit_logs_db
from app.routers.projects import projects_db
from app.routers.fileslifecycle import files_db
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics: Usage Analytics"])


@router.get("/users", response_model=UsersAnalyticsOut)
def get_users_analytics(current_user: dict = Depends(get_current_user)):
    return UsersAnalyticsOut(
        total_users=len(users_db),
        total_admins=sum(1 for u in users_db.values() if u.get("is_admin", False)),
        total_suspended=sum(1 for u in users_db.values() if u.get("suspended", False)),
    )


@router.get("/projects", response_model=ProjectsAnalyticsOut)
def get_projects_analytics(current_user: dict = Depends(get_current_user)):
    active = sum(1 for p in projects_db.values() if p["status"] == "active")
    archived = sum(1 for p in projects_db.values() if p["status"] == "archived")
    return ProjectsAnalyticsOut(
        total_projects=len(projects_db),
        active_projects=active,
        archived_projects=archived,
    )


@router.get("/models", response_model=ModelsAnalyticsOut)
def get_models_analytics(current_user: dict = Depends(get_current_user)):
    # STUB: no dedicated models domain exists yet.
    return ModelsAnalyticsOut(total_models=0, total_inferences=0)


@router.get("/tokens", response_model=TokensAnalyticsOut)
def get_tokens_analytics(current_user: dict = Depends(get_current_user)):
    # STUB: simulated, derived from overall audit activity.
    count = len(audit_logs_db)
    return TokensAnalyticsOut(total_tokens=count * 450, period="current_month")


@router.get("/storage", response_model=StorageAnalyticsOut)
def get_storage_analytics(current_user: dict = Depends(get_current_user)):
    return StorageAnalyticsOut(
        total_files=len(files_db),
        total_bytes=sum(f["size_bytes"] for f in files_db.values()),
    )