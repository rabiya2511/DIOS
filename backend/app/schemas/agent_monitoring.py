"""
Schemas for the Monitoring group of the Agents & Planning APIs blueprint.
Named agent_monitoring to avoid colliding with the existing platform
monitoring.py domain (monitoring / monitoring_metrics / monitoring_logs /
monitoring_alerts / monitoring_tracing / monitoring_admin).
"""

from datetime import datetime
from typing import Optional, List, Literal

from pydantic import BaseModel, EmailStr, Field

HealthLevel = Literal["healthy", "degraded", "unhealthy"]
LogLevel = Literal["info", "warning", "error"]


class AgentMetricsResponse(BaseModel):
    total_agents: int
    active_agents: int
    archived_agents: int
    disabled_agents: int
    computed_at: datetime


class AgentUsageEntry(BaseModel):
    agent_id: str
    agent_name: str
    tasks_assigned: int
    tool_invocations: int


class AgentUsageResponse(BaseModel):
    total_agents: int
    usage: List[AgentUsageEntry]
    computed_at: datetime


class AgentHealthEntry(BaseModel):
    agent_id: str
    agent_name: str
    status: str
    health: HealthLevel
    recent_error_count: int


class AgentHealthResponse(BaseModel):
    overall_health: HealthLevel
    agents: List[AgentHealthEntry]
    checked_at: datetime


class AgentLogEntry(BaseModel):
    id: str
    agent_id: str
    level: LogLevel
    message: str
    timestamp: datetime


class AgentLogListResponse(BaseModel):
    total: int
    items: List[AgentLogEntry]


class AgentAuditEntry(BaseModel):
    id: str
    actor_email: EmailStr
    agent_id: Optional[str] = None
    action: str
    timestamp: datetime


class AgentAuditListResponse(BaseModel):
    total: int
    items: List[AgentAuditEntry]


class AgentErrorEntry(BaseModel):
    id: str
    agent_id: str
    error_type: str
    message: str
    timestamp: datetime


class AgentErrorListResponse(BaseModel):
    total: int
    items: List[AgentErrorEntry]


class CacheClearResponse(BaseModel):
    cleared: bool
    cleared_at: datetime


class AgentPerformanceEntry(BaseModel):
    agent_id: str
    agent_name: str
    tasks_completed: int
    tasks_failed: int
    tool_invocations_success: int
    tool_invocations_failed: int
    success_rate: float = Field(..., ge=0.0, le=1.0)


class AgentPerformanceResponse(BaseModel):
    agents: List[AgentPerformanceEntry]
    computed_at: datetime