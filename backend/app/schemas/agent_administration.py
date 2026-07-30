"""
Agent Administration router — enable, disable, config, reindex,
reload, policies. Matches the Administration section of the Agents &
Planning APIs blueprint (8/8). Reuses agents_db from agent_lifecycle.py.

*** ROUTING WARNING ***
Same hazard as agent_monitoring.py: /agents/enable, /disable, /config,
/reindex, /reload, /policies are all single path segments under
/api/v1/agents, the same shape as agent_lifecycle.py's dynamic
GET/PATCH/DELETE /agents/{id}. This router's app.include_router call
MUST be added to main.py BEFORE agent_lifecycle.router — same
requirement documented in agent_monitoring.py.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.agent_administration import (
    AgentIdBodyRequest,
    AgentEnableResponse,
    AgentConfigUpdateRequest,
    AgentConfigResponse,
    AgentReindexResponse,
    AgentReloadResponse,
    AgentPolicyCreateRequest,
    AgentPolicyResponse,
    AgentPolicyListResponse,
)
from app.core.security import get_current_user
from app.routers.agent_lifecycle import agents_db

router = APIRouter(prefix="/api/v1/agents", tags=["Agent Administration"])

# id -> {id, agent_id, policy, created_at}
agent_policies_db: dict[str, dict] = {}


def _get_owned_agent(agent_id: str, email: str) -> dict:
    agent = agents_db.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent["owner_email"] != email:
        raise HTTPException(status_code=403, detail="Only the agent owner can perform this action")
    return agent


@router.post("/enable", response_model=AgentEnableResponse)
def enable_agent(data: AgentIdBodyRequest, current_user: dict = Depends(get_current_user)):
    agent = _get_owned_agent(data.agent_id, current_user["email"])
    agent["status"] = "active"
    agent["updated_at"] = datetime.now(timezone.utc)
    return AgentEnableResponse(agent_id=agent["id"], status=agent["status"])


@router.post("/disable", response_model=AgentEnableResponse)
def disable_agent(data: AgentIdBodyRequest, current_user: dict = Depends(get_current_user)):
    agent = _get_owned_agent(data.agent_id, current_user["email"])
    agent["status"] = "disabled"
    agent["updated_at"] = datetime.now(timezone.utc)
    return AgentEnableResponse(agent_id=agent["id"], status=agent["status"])


@router.patch("/config", response_model=AgentConfigResponse)
def update_agent_config(
    data: AgentConfigUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    agent = _get_owned_agent(data.agent_id, current_user["email"])
    agent.setdefault("config", {}).update(data.config)
    agent["updated_at"] = datetime.now(timezone.utc)
    return AgentConfigResponse(agent_id=agent["id"], config=agent["config"])


@router.get("/config", response_model=AgentConfigResponse)
def get_agent_config(agent_id: str, current_user: dict = Depends(get_current_user)):
    agent = _get_owned_agent(agent_id, current_user["email"])
    return AgentConfigResponse(agent_id=agent["id"], config=agent.get("config", {}))


@router.post("/reindex", response_model=AgentReindexResponse)
def reindex_agents(current_user: dict = Depends(get_current_user)):
    # STUB: real version would rebuild search/embedding indexes for the
    # caller's agents; here it just counts them and reports success.
    owned = [a for a in agents_db.values() if a["owner_email"] == current_user["email"]]
    return AgentReindexResponse(reindexed_count=len(owned), completed_at=datetime.now(timezone.utc))


@router.post("/reload", response_model=AgentReloadResponse)
def reload_agent(data: AgentIdBodyRequest, current_user: dict = Depends(get_current_user)):
    agent = _get_owned_agent(data.agent_id, current_user["email"])
    # STUB: real version would reload the agent's runtime config/model binding.
    return AgentReloadResponse(agent_id=agent["id"], reloaded=True, reloaded_at=datetime.now(timezone.utc))


@router.post("/policies", response_model=AgentPolicyResponse, status_code=201)
def create_agent_policy(
    data: AgentPolicyCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    _get_owned_agent(data.agent_id, current_user["email"])
    policy_id = str(uuid4())
    now = datetime.now(timezone.utc)
    agent_policies_db[policy_id] = {
        "id": policy_id,
        "agent_id": data.agent_id,
        "policy": data.policy,
        "created_at": now,
    }
    return agent_policies_db[policy_id]


@router.get("/policies", response_model=AgentPolicyListResponse)
def list_agent_policies(agent_id: str, current_user: dict = Depends(get_current_user)):
    _get_owned_agent(agent_id, current_user["email"])
    items = [p for p in agent_policies_db.values() if p["agent_id"] == agent_id]
    return AgentPolicyListResponse(total=len(items), items=items)