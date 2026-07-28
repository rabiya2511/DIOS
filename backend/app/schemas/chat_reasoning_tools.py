"""
Schemas for the Reasoning & Tools group of the AI Chat APIs blueprint.
Endpoints covered:
  POST /api/v1/chat/reason
  POST /api/v1/chat/search
  POST /api/v1/chat/browser
  POST /api/v1/chat/python
  POST /api/v1/chat/database
  POST /api/v1/chat/files
  POST /api/v1/chat/calendar
  POST /api/v1/chat/email
  POST /api/v1/chat/webhook
  POST /api/v1/chat/workflow
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, EmailStr, Field


# ---------- Reason ----------

class ReasonRequest(BaseModel):
    chat_id: str
    query: str = Field(..., description="Question or task to reason through")
    effort: Literal["low", "medium", "high"] = "medium"


class ReasonResponse(BaseModel):
    id: str
    chat_id: str
    query: str
    reasoning_steps: List[str]
    conclusion: str
    created_at: datetime


# ---------- Search ----------

class SearchToolRequest(BaseModel):
    chat_id: str
    query: str
    max_results: int = Field(5, ge=1, le=20)


class SearchResultItem(BaseModel):
    title: str
    url: str
    snippet: str


class SearchToolResponse(BaseModel):
    id: str
    chat_id: str
    query: str
    results: List[SearchResultItem]
    created_at: datetime


# ---------- Browser ----------

class BrowserToolRequest(BaseModel):
    chat_id: str
    url: str
    action: Literal["read", "click", "screenshot"] = "read"


class BrowserToolResponse(BaseModel):
    id: str
    chat_id: str
    url: str
    action: str
    content_summary: str
    created_at: datetime


# ---------- Python ----------

class PythonExecuteRequest(BaseModel):
    chat_id: str
    code: str


class PythonExecuteResponse(BaseModel):
    id: str
    chat_id: str
    stdout: str
    stderr: str
    success: bool
    created_at: datetime


# ---------- Database ----------

class DatabaseQueryRequest(BaseModel):
    chat_id: str
    query: str = Field(..., description="Query text, e.g. SQL")
    connection_id: Optional[str] = None


class DatabaseQueryResponse(BaseModel):
    id: str
    chat_id: str
    rows: List[Dict[str, Any]]
    row_count: int
    created_at: datetime


# ---------- Files ----------

class FileToolRequest(BaseModel):
    chat_id: str
    operation: Literal["read", "write", "list"]
    path: str
    content: Optional[str] = Field(None, description="Content to write, required when operation=write")


class FileToolResponse(BaseModel):
    id: str
    chat_id: str
    operation: str
    path: str
    result: str
    created_at: datetime


# ---------- Calendar ----------

class CalendarEvent(BaseModel):
    title: str
    start_time: datetime
    end_time: datetime
    attendees: Optional[List[str]] = Field(default_factory=list)


class CalendarToolRequest(BaseModel):
    chat_id: str
    action: Literal["create_event", "list_events"]
    event: Optional[CalendarEvent] = None


class CalendarToolResponse(BaseModel):
    id: str
    chat_id: str
    action: str
    events: List[Dict[str, Any]]
    created_at: datetime


# ---------- Email ----------

class EmailToolRequest(BaseModel):
    chat_id: str
    to: EmailStr
    subject: str
    body: str
    action: Literal["send", "draft"] = "send"


class EmailToolResponse(BaseModel):
    id: str
    chat_id: str
    to: EmailStr
    subject: str
    status: str
    created_at: datetime


# ---------- Webhook ----------

class WebhookToolRequest(BaseModel):
    chat_id: str
    url: str
    payload: Dict[str, Any] = Field(default_factory=dict)


class WebhookToolResponse(BaseModel):
    id: str
    chat_id: str
    url: str
    delivered: bool
    created_at: datetime


# ---------- Workflow ----------

class WorkflowToolRequest(BaseModel):
    chat_id: str
    workflow_name: str
    params: Dict[str, Any] = Field(default_factory=dict)


class WorkflowToolResponse(BaseModel):
    id: str
    chat_id: str
    workflow_name: str
    run_id: str
    status: str
    created_at: datetime