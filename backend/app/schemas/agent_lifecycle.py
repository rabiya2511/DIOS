"""
Agent Lifecycle router — CRUD, archive, restore, clone.
Matches the Agent Lifecycle section of the Agents & Planning APIs
blueprint (8/8). Only the agent owner can update/delete/archive/
restore/clone their own agent — same ownership model as
conversations.py.

Literal-path routes (/archive, /restore, /clone) MUST come before the
dynamic /{id} routes below — same ordering rule as conversations.py /
fileslifecycle.py.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.agent_lifecycle import (
    AgentCreateRequest,
    AgentUpdateRequest,
    AgentResponse,
    AgentIdBodyRequest,
    AgentCloneRequest,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/agents", tags=["Agent Lifecycle"])

# id -> {id, owner_email, name, description, model_id, instructions, tools, config, status, created_at, updated_at}
agents_db: dict[str, dict] = {}


def _get_agent_or_404(agent_id: str) -> dict:
    agent = agents_db.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


def _require_owner(agent: dict, email: str):
    if agent["owner_email"] != email:
        raise HTTPException(status_code=403, detail="Only the agent owner can perform this action")


@router.get("", response_model=list[AgentResponse])
def list_agents(current_user: dict = Depends(get_current_user)):
    return [a for a in agents_db.values() if a["owner_email"] == current_user["email"]]


@router.post("", response_model=AgentResponse, status_code=201)
def create_agent(
    data: AgentCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    agent_id = str(uuid4())
    now = datetime.now(timezone.utc)
    agents_db[agent_id] = {
        "id": agent_id,
        "owner_email": current_user["email"],
        "name": data.name,
        "description": data.description,
        "model_id": data.model_id,
        "instructions": data.instructions,
        "tools": data.tools,
        "config": data.config,
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }
    return agents_db[agent_id]


# ─── Literal-path routes MUST come before any /{id} routes below ───

@router.post("/archive", response_model=AgentResponse)
def archive_agent(
    data: AgentIdBodyRequest,
    current_user: dict = Depends(get_current_user),
):
    agent = _get_agent_or_404(data.agent_id)
    _require_owner(agent, current_user["email"])
    agent["status"] = "archived"
    agent["updated_at"] = datetime.now(timezone.utc)
    return agent


@router.post("/restore", response_model=AgentResponse)
def restore_agent(
    data: AgentIdBodyRequest,
    current_user: dict = Depends(get_current_user),
):
    agent = _get_agent_or_404(data.agent_id)
    _require_owner(agent, current_user["email"])
    agent["status"] = "active"
    agent["updated_at"] = datetime.now(timezone.utc)
    return agent


@router.post("/clone", response_model=AgentResponse, status_code=201)
def clone_agent(
    data: AgentCloneRequest,
    current_user: dict = Depends(get_current_user),
):
    original = _get_agent_or_404(data.agent_id)
    _require_owner(original, current_user["email"])

    new_id = str(uuid4())
    now = datetime.now(timezone.utc)
    agents_db[new_id] = {
        "id": new_id,
        "owner_email": current_user["email"],
        "name": data.new_name or f"{original['name']} (copy)",
        "description": original["description"],
        "model_id": original["model_id"],
        "instructions": original["instructions"],
        "tools": list(original["tools"]),
        "config": dict(original["config"]),
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }
    return agents_db[new_id]


# ─── Dynamic /{id} routes come LAST ───

@router.get("/{id}", response_model=AgentResponse)
def get_agent(id: str, current_user: dict = Depends(get_current_user)):
    agent = _get_agent_or_404(id)
    _require_owner(agent, current_user["email"])
    return agent


@router.patch("/{id}", response_model=AgentResponse)
def update_agent(
    id: str,
    data: AgentUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    agent = _get_agent_or_404(id)
    _require_owner(agent, current_user["email"])

    update_data = data.model_dump(exclude_unset=True)
    agent.update(update_data)
    agent["updated_at"] = datetime.now(timezone.utc)
    return agent


@router.delete("/{id}", status_code=204)
def delete_agent(id: str, current_user: dict = Depends(get_current_user)):
    agent = _get_agent_or_404(id)
    _require_owner(agent, current_user["email"])
    del agents_db[id]
    return None