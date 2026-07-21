"""
Pydantic schemas for the Logs domain (Monitoring APIs blueprint).
Application/system-level logs, seeded with sample entries — distinct
from the user-action audit trail in audit_logs_db.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

LogLevel = Literal["info", "warning", "error"]


class LogEntryResponse(BaseModel):
    id: str
    level: LogLevel
    message: str
    source: str
    timestamp: datetime


class LogSearchRequest(BaseModel):
    query: str | None = None  # substring match against message
    level: LogLevel | None = None