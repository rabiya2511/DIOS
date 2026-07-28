"""
Schemas for the Prompt & Context group of the AI Chat APIs blueprint.
Endpoints covered:
  POST /api/v1/chat/system-prompt
  GET  /api/v1/chat/system-prompt
  POST /api/v1/chat/context
  GET  /api/v1/chat/context
  POST /api/v1/chat/context/clear
  POST /api/v1/chat/template
  GET  /api/v1/chat/templates
  POST /api/v1/chat/template/apply
  POST /api/v1/chat/variables
  POST /api/v1/chat/context/window
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ---------- System Prompt ----------

class SystemPromptSetRequest(BaseModel):
    chat_id: str = Field(..., description="Chat/conversation this system prompt applies to")
    content: str = Field(..., description="The system prompt text")


class SystemPromptResponse(BaseModel):
    chat_id: str
    content: str
    updated_at: datetime


# ---------- Context ----------

class ContextSetRequest(BaseModel):
    chat_id: str
    data: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary context payload")


class ContextResponse(BaseModel):
    chat_id: str
    data: Dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime


class ContextClearRequest(BaseModel):
    chat_id: str


class ContextClearResponse(BaseModel):
    chat_id: str
    cleared: bool
    message: str


class ContextWindowSetRequest(BaseModel):
    chat_id: str
    window_size: int = Field(..., ge=1, description="Number of prior messages/tokens to retain")


class ContextWindowResponse(BaseModel):
    chat_id: str
    window_size: int
    updated_at: datetime


# ---------- Templates ----------

class ChatTemplateCreateRequest(BaseModel):
    name: str
    content: str = Field(..., description="Template body, may include {variable} placeholders")
    description: Optional[str] = None


class ChatTemplateOut(BaseModel):
    id: str
    name: str
    content: str
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ChatTemplateListResponse(BaseModel):
    total: int
    items: List[ChatTemplateOut]


class ChatTemplateApplyRequest(BaseModel):
    chat_id: str
    template_id: str
    variables: Optional[Dict[str, str]] = Field(default_factory=dict)


class ChatTemplateApplyResponse(BaseModel):
    chat_id: str
    template_id: str
    rendered_content: str
    applied_at: datetime


# ---------- Variables ----------

class ChatVariablesSetRequest(BaseModel):
    chat_id: str
    variables: Dict[str, str] = Field(default_factory=dict)


class ChatVariablesResponse(BaseModel):
    chat_id: str
    variables: Dict[str, str] = Field(default_factory=dict)
    updated_at: datetime