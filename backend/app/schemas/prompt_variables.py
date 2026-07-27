"""
Pydantic schemas for the Variables & Context domain (Prompt Management
APIs blueprint). Variables are reusable named values (e.g. {{user_name}})
a user can reference across prompts; context is an assembled blob built
from those variables plus manual overrides.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class PromptVariableCreateRequest(BaseModel):
    name: str
    value: str
    description: str | None = None


class PromptVariableUpdateRequest(BaseModel):
    value: str | None = None
    description: str | None = None


class PromptVariableResponse(BaseModel):
    id: str
    name: str
    value: str
    description: str | None = None
    created_at: datetime
    updated_at: datetime


class ContextBuildResponse(BaseModel):
    assembled_text: str
    variables_used: list[str]
    updated_at: datetime


class ContextResponse(BaseModel):
    assembled_text: str
    variables_used: list[str]
    updated_at: datetime | None = None


class ContextUpdateRequest(BaseModel):
    extra: dict[str, Any] = {}  # merged into assembled_text as additional "key: value" lines


class ContextDeleteResponse(BaseModel):
    cleared: bool