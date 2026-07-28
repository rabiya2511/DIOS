"""
Router for the Prompt & Context group of the AI Chat APIs blueprint.
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

Named chat_prompt_context.py (not templates.py / context_memory.py) to
avoid colliding with existing routers of similar purpose elsewhere in
the DIOS app. Uses local in-memory dicts (same pattern as
conversations_db in conversations.py) — swap for real persistence when
wiring this up.

No dynamic /{id} path params are used here (endpoints take chat_id /
template_id as query params or in the request body), so there's no
literal-vs-dynamic route ordering concern in this file.
"""

import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.schemas.chat_prompt_context import (
    SystemPromptSetRequest,
    SystemPromptResponse,
    ContextSetRequest,
    ContextResponse,
    ContextClearRequest,
    ContextClearResponse,
    ContextWindowSetRequest,
    ContextWindowResponse,
    ChatTemplateCreateRequest,
    ChatTemplateOut,
    ChatTemplateListResponse,
    ChatTemplateApplyRequest,
    ChatTemplateApplyResponse,
    ChatVariablesSetRequest,
    ChatVariablesResponse,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/chat", tags=["Chat Prompt & Context"])

# chat_id -> {content, updated_at}
system_prompts_db: dict[str, dict] = {}
# chat_id -> {data, updated_at}
chat_context_db: dict[str, dict] = {}
# chat_id -> {window_size, updated_at}
chat_context_window_db: dict[str, dict] = {}
# id -> {id, name, content, description, created_at}
chat_templates_db: dict[str, dict] = {}
# chat_id -> {variables, updated_at}
chat_variables_db: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# POST /api/v1/chat/system-prompt
# ---------------------------------------------------------------------------
@router.post("/system-prompt", response_model=SystemPromptResponse)
def set_system_prompt(
    payload: SystemPromptSetRequest,
    current_user: dict = Depends(get_current_user),
):
    """Set (or replace) the system prompt for a chat."""
    now = datetime.now(timezone.utc)
    system_prompts_db[payload.chat_id] = {"content": payload.content, "updated_at": now}
    return SystemPromptResponse(chat_id=payload.chat_id, content=payload.content, updated_at=now)


# ---------------------------------------------------------------------------
# GET /api/v1/chat/system-prompt
# ---------------------------------------------------------------------------
@router.get("/system-prompt", response_model=SystemPromptResponse)
def get_system_prompt(
    chat_id: str = Query(...),
    current_user: dict = Depends(get_current_user),
):
    """Retrieve the current system prompt for a chat."""
    entry = system_prompts_db.get(chat_id)
    if not entry:
        raise HTTPException(status_code=404, detail="No system prompt set for this chat")
    return SystemPromptResponse(chat_id=chat_id, content=entry["content"], updated_at=entry["updated_at"])


# ---------------------------------------------------------------------------
# POST /api/v1/chat/context
# ---------------------------------------------------------------------------
@router.post("/context", response_model=ContextResponse)
def set_context(
    payload: ContextSetRequest,
    current_user: dict = Depends(get_current_user),
):
    """Set (merge/replace) context data for a chat."""
    now = datetime.now(timezone.utc)
    chat_context_db[payload.chat_id] = {"data": payload.data, "updated_at": now}
    return ContextResponse(chat_id=payload.chat_id, data=payload.data, updated_at=now)


# ---------------------------------------------------------------------------
# GET /api/v1/chat/context
# ---------------------------------------------------------------------------
@router.get("/context", response_model=ContextResponse)
def get_context(
    chat_id: str = Query(...),
    current_user: dict = Depends(get_current_user),
):
    """Retrieve context data for a chat."""
    entry = chat_context_db.get(chat_id)
    if not entry:
        raise HTTPException(status_code=404, detail="No context set for this chat")
    return ContextResponse(chat_id=chat_id, data=entry["data"], updated_at=entry["updated_at"])


# ---------------------------------------------------------------------------
# POST /api/v1/chat/context/clear
# ---------------------------------------------------------------------------
@router.post("/context/clear", response_model=ContextClearResponse)
def clear_context(
    payload: ContextClearRequest,
    current_user: dict = Depends(get_current_user),
):
    """Clear stored context data for a chat."""
    existed = chat_context_db.pop(payload.chat_id, None) is not None
    return ContextClearResponse(
        chat_id=payload.chat_id,
        cleared=existed,
        message="Context cleared" if existed else "No context existed for this chat",
    )


# ---------------------------------------------------------------------------
# POST /api/v1/chat/context/window
# ---------------------------------------------------------------------------
@router.post("/context/window", response_model=ContextWindowResponse)
def set_context_window(
    payload: ContextWindowSetRequest,
    current_user: dict = Depends(get_current_user),
):
    """Configure how much prior context (messages/tokens) a chat retains."""
    now = datetime.now(timezone.utc)
    chat_context_window_db[payload.chat_id] = {"window_size": payload.window_size, "updated_at": now}
    return ContextWindowResponse(chat_id=payload.chat_id, window_size=payload.window_size, updated_at=now)


# ---------------------------------------------------------------------------
# POST /api/v1/chat/template
# ---------------------------------------------------------------------------
@router.post("/template", response_model=ChatTemplateOut, status_code=status.HTTP_201_CREATED)
def create_chat_template(
    payload: ChatTemplateCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    """Create a reusable chat prompt template."""
    template_id = str(uuid.uuid4())
    template = {
        "id": template_id,
        "name": payload.name,
        "content": payload.content,
        "description": payload.description,
        "created_at": datetime.now(timezone.utc),
    }
    chat_templates_db[template_id] = template
    return template


# ---------------------------------------------------------------------------
# GET /api/v1/chat/templates
# ---------------------------------------------------------------------------
@router.get("/templates", response_model=ChatTemplateListResponse)
def list_chat_templates(
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    """List available chat prompt templates."""
    items = list(chat_templates_db.values())
    total = len(items)
    items = items[offset: offset + limit]
    return ChatTemplateListResponse(total=total, items=items)


# ---------------------------------------------------------------------------
# POST /api/v1/chat/template/apply
# ---------------------------------------------------------------------------
@router.post("/template/apply", response_model=ChatTemplateApplyResponse)
def apply_chat_template(
    payload: ChatTemplateApplyRequest,
    current_user: dict = Depends(get_current_user),
):
    """Render a template's {variable} placeholders and apply it to a chat."""
    template = chat_templates_db.get(payload.template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    rendered = template["content"]
    for key, value in (payload.variables or {}).items():
        rendered = re.sub(r"\{" + re.escape(key) + r"\}", value, rendered)

    now = datetime.now(timezone.utc)
    # Applying a template sets it as the chat's active system prompt.
    system_prompts_db[payload.chat_id] = {"content": rendered, "updated_at": now}

    return ChatTemplateApplyResponse(
        chat_id=payload.chat_id,
        template_id=payload.template_id,
        rendered_content=rendered,
        applied_at=now,
    )


# ---------------------------------------------------------------------------
# POST /api/v1/chat/variables
# ---------------------------------------------------------------------------
@router.post("/variables", response_model=ChatVariablesResponse)
def set_chat_variables(
    payload: ChatVariablesSetRequest,
    current_user: dict = Depends(get_current_user),
):
    """Set template variables available to a chat."""
    now = datetime.now(timezone.utc)
    chat_variables_db[payload.chat_id] = {"variables": payload.variables, "updated_at": now}
    return ChatVariablesResponse(chat_id=payload.chat_id, variables=payload.variables, updated_at=now)