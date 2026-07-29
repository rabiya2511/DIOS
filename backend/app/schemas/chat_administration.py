"""
Schemas for the Administration group of the AI Chat APIs blueprint.
Endpoints covered:
  GET  /api/v1/chat/metrics
  GET  /api/v1/chat/usage
  GET  /api/v1/chat/audit
  POST /api/v1/chat/moderate
  POST /api/v1/chat/feedback
  GET  /api/v1/chat/health
  POST /api/v1/chat/cache/clear
  GET  /api/v1/chat/config
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field


# ---------- Metrics ----------

class ChatMetricsResponse(BaseModel):
    total_chats: int
    total_messages: int
    active_chats_last_24h: int
    avg_response_time_ms: float
    generated_at: datetime


# ---------- Usage ----------

class ChatUsageResponse(BaseModel):
    chat_id: Optional[str] = None
    total_tokens: int
    total_requests: int
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    generated_at: datetime


# ---------- Audit ----------

class ChatAuditLogEntry(BaseModel):
    id: str
    actor_email: str
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    detail: Optional[str] = None
    timestamp: datetime


class ChatAuditLogResponse(BaseModel):
    total: int
    items: List[ChatAuditLogEntry]


# ---------- Moderate ----------

class ModerateRequest(BaseModel):
    chat_id: str
    message_id: Optional[str] = None
    content: str = Field(..., description="Text content to run through moderation")


class ModerateResponse(BaseModel):
    id: str
    chat_id: str
    message_id: Optional[str] = None
    flagged: bool
    categories: List[str] = Field(default_factory=list)
    action_taken: str
    created_at: datetime


# ---------- Feedback ----------

class FeedbackRequest(BaseModel):
    chat_id: str
    message_id: Optional[str] = None
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None


class FeedbackResponse(BaseModel):
    id: str
    chat_id: str
    message_id: Optional[str] = None
    rating: int
    comment: Optional[str] = None
    created_at: datetime


# ---------- Health ----------

class ChatHealthResponse(BaseModel):
    status: Literal["ok", "degraded", "down"]
    uptime_seconds: float
    checked_at: datetime


# ---------- Cache Clear ----------

class CacheClearRequest(BaseModel):
    scope: Literal["all", "chat", "model"] = "all"
    chat_id: Optional[str] = Field(None, description="Required when scope='chat'")


class CacheClearResponse(BaseModel):
    scope: str
    chat_id: Optional[str] = None
    cleared: bool
    cleared_at: datetime


# ---------- Config ----------

class ChatConfigResponse(BaseModel):
    features: Dict[str, bool]
    limits: Dict[str, int]
    updated_at: datetime