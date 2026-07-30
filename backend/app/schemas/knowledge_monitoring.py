"""
Schemas for the Monitoring group of the Knowledge/RAG APIs blueprint.
Endpoints covered:
  GET  /api/v1/knowledge/metrics
  GET  /api/v1/knowledge/usage
  GET  /api/v1/knowledge/health
  GET  /api/v1/knowledge/logs
  GET  /api/v1/knowledge/audit
  GET  /api/v1/knowledge/errors
  POST /api/v1/knowledge/cache/clear
  GET  /api/v1/knowledge/performance
"""

from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field


# ---------- Metrics ----------

class KnowledgeMetricsResponse(BaseModel):
    total_documents: int
    total_chunks: int
    total_embeddings: int
    avg_query_latency_ms: float
    generated_at: datetime


# ---------- Usage ----------

class KnowledgeUsageResponse(BaseModel):
    total_queries: int
    total_tokens_embedded: int
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    generated_at: datetime


# ---------- Health ----------

class KnowledgeHealthResponse(BaseModel):
    status: Literal["ok", "degraded", "down"]
    uptime_seconds: float
    checked_at: datetime


# ---------- Logs ----------

class KnowledgeLogEntry(BaseModel):
    id: str
    level: Literal["INFO", "WARNING", "ERROR"]
    message: str
    timestamp: datetime


class KnowledgeLogsResponse(BaseModel):
    total: int
    items: List[KnowledgeLogEntry]


# ---------- Audit ----------

class KnowledgeAuditEntry(BaseModel):
    id: str
    actor_email: str
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    detail: Optional[str] = None
    timestamp: datetime


class KnowledgeAuditResponse(BaseModel):
    total: int
    items: List[KnowledgeAuditEntry]


# ---------- Errors ----------

class KnowledgeErrorEntry(BaseModel):
    id: str
    error_type: str
    message: str
    resource_id: Optional[str] = None
    timestamp: datetime


class KnowledgeErrorsResponse(BaseModel):
    total: int
    items: List[KnowledgeErrorEntry]


# ---------- Cache Clear ----------

class KnowledgeCacheClearRequest(BaseModel):
    scope: Literal["all", "embeddings", "vectors"] = "all"


class KnowledgeCacheClearResponse(BaseModel):
    scope: str
    cleared: bool
    cleared_at: datetime


# ---------- Performance ----------

class KnowledgePerformanceResponse(BaseModel):
    avg_query_latency_ms: float
    p95_latency_ms: float
    avg_indexing_time_ms: float
    generated_at: datetime