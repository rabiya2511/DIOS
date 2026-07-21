"""
Pydantic schemas for the Audit domain (user/org/role scoped views).
Reuses the general-purpose audit_logs_db, filtered by action category.
"""

from datetime import datetime

from pydantic import BaseModel


class DomainAuditEntryOut(BaseModel):
    actor_email: str
    action: str
    timestamp: datetime