"""
Pydantic schemas for the Audit & Compliance domain (Authorization blueprint).
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AuthzAuditEntryOut(BaseModel):
    id: str
    actor_email: str
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    timestamp: datetime
    archived: bool = False


class AuthzLogEntryOut(BaseModel):
    actor_email: str
    action: str
    timestamp: datetime


class AuthzReportOut(BaseModel):
    generated_at: datetime
    total_audit_entries: int
    total_login_events: int
    total_reviews: int
    total_violations: int


class AuthzViolationOut(BaseModel):
    id: str
    actor_email: str
    action: str
    reason: str
    timestamp: datetime


class ReviewRequest(BaseModel):
    note: str


class ReviewOut(BaseModel):
    id: str
    reviewer_email: str
    note: str
    timestamp: datetime


class ArchiveResponse(BaseModel):
    archived_count: int
    timestamp: datetime