"""
Pydantic schemas for the Tracing domain (Monitoring APIs blueprint).
Seeded with sample distributed-tracing data (traces + spans).
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

TraceStatus = Literal["ok", "error"]


class TraceResponse(BaseModel):
    id: str
    name: str
    status: TraceStatus
    duration_ms: float
    started_at: datetime


class SpanResponse(BaseModel):
    id: str
    trace_id: str
    name: str
    duration_ms: float
    started_at: datetime


class TraceSearchRequest(BaseModel):
    query: str | None = None  # substring match against name
    status: TraceStatus | None = None