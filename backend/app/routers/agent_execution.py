"""
Agent Execution router — run/stop/pause/resume/status/history/retry/cancel.
Matches the Agent Execution section of the Agents & Planning APIs
blueprint (8/8).

Depends on agents_db from agent_lifecycle.py to validate that an
agent exists and belongs to the requesting user before allowing any
execution action against it — same cross-router pattern as
messages.py depending on conversations_db.

All 8 routes live under /api/v1/agents/{id}/... — since every path
here has a literal action suffix after {id} (run, stop, pause, etc.),
there's no collision with agent_lifecycle.py's bare GET/PATCH/DELETE
/api/v1/agents/{id} routes; they're simply different full paths.
"""

from datetime import datetime, timezone
from uuid import uuid4
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.agent_execution import (
    AgentRunRequest,
    ExecutionActionRequest,
    ExecutionResponse,
    ExecutionHistoryResponse,
    AgentStatusResponse,
)
from app.core.security import get_current_user
from app.routers.agent_lifecycle import agents_db

router = APIRouter(prefix="/api/v1/agents", tags=["Agent Execution"])

# id -> {id, agent_id, owner_email, status, task, input, output, error, started_at, ended_at, updated_at}
executions_db: dict[str, dict] = {}


def _get_agent_or_404(agent_id: str) -> dict:
    agent = agents_db.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


def _require_owner(agent: dict, email: str):
    if agent["owner_email"] != email:
        raise HTTPException(status_code=403, detail="Only the agent owner can perform this action")


def _executions_for_agent(agent_id: str) -> list[dict]:
    return sorted(
        (e for e in executions_db.values() if e["agent_id"] == agent_id),
        key=lambda e: e["started_at"],
        reverse=True,
    )


def _resolve_execution(agent_id: str, execution_id: Optional[str]) -> dict:
    if execution_id:
        execution = executions_db.get(execution_id)
        if not execution or execution["agent_id"] != agent_id:
            raise HTTPException(status_code=404, detail="Execution not found for this agent")
        return execution

    recent = _executions_for_agent(agent_id)
    if not recent:
        raise HTTPException(status_code=404, detail="This agent has no executions yet")
    return recent[0]


# ---------------------------------------------------------------------------
# POST /api/v1/agents/{id}/run
# ---------------------------------------------------------------------------
@router.post("/{id}/run", response_model=ExecutionResponse, status_code=201)
def run_agent(
    id: str,
    payload: AgentRunRequest,
    current_user: dict = Depends(get_current_user),
):
    """Start a new execution run for an agent."""
    agent = _get_agent_or_404(id)
    _require_owner(agent, current_user["email"])

    execution_id = str(uuid4())
    now = datetime.now(timezone.utc)
    execution = {
        "id": execution_id,
        "agent_id": id,
        "owner_email": current_user["email"],
        "status": "running",
        "task": payload.task,
        "input": payload.input,
        "output": None,
        "error": None,
        "started_at": now,
        "ended_at": None,
        "updated_at": now,
    }
    executions_db[execution_id] = execution
    return execution


# ---------------------------------------------------------------------------
# POST /api/v1/agents/{id}/stop
# ---------------------------------------------------------------------------
@router.post("/{id}/stop", response_model=ExecutionResponse)
def stop_agent(
    id: str,
    payload: ExecutionActionRequest,
    current_user: dict = Depends(get_current_user),
):
    """Stop a running or paused execution."""
    agent = _get_agent_or_404(id)
    _require_owner(agent, current_user["email"])
    execution = _resolve_execution(id, payload.execution_id)

    if execution["status"] not in ("running", "paused"):
        raise HTTPException(status_code=400, detail=f"Cannot stop an execution in status '{execution['status']}'")

    now = datetime.now(timezone.utc)
    execution["status"] = "stopped"
    execution["ended_at"] = now
    execution["updated_at"] = now
    return execution


# ---------------------------------------------------------------------------
# POST /api/v1/agents/{id}/pause
# ---------------------------------------------------------------------------
@router.post("/{id}/pause", response_model=ExecutionResponse)
def pause_agent(
    id: str,
    payload: ExecutionActionRequest,
    current_user: dict = Depends(get_current_user),
):
    """Pause a running execution."""
    agent = _get_agent_or_404(id)
    _require_owner(agent, current_user["email"])
    execution = _resolve_execution(id, payload.execution_id)

    if execution["status"] != "running":
        raise HTTPException(status_code=400, detail=f"Cannot pause an execution in status '{execution['status']}'")

    execution["status"] = "paused"
    execution["updated_at"] = datetime.now(timezone.utc)
    return execution


# ---------------------------------------------------------------------------
# POST /api/v1/agents/{id}/resume
# ---------------------------------------------------------------------------
@router.post("/{id}/resume", response_model=ExecutionResponse)
def resume_agent(
    id: str,
    payload: ExecutionActionRequest,
    current_user: dict = Depends(get_current_user),
):
    """Resume a paused execution."""
    agent = _get_agent_or_404(id)
    _require_owner(agent, current_user["email"])
    execution = _resolve_execution(id, payload.execution_id)

    if execution["status"] != "paused":
        raise HTTPException(status_code=400, detail=f"Cannot resume an execution in status '{execution['status']}'")

    execution["status"] = "running"
    execution["updated_at"] = datetime.now(timezone.utc)
    return execution


# ---------------------------------------------------------------------------
# GET /api/v1/agents/{id}/status
# ---------------------------------------------------------------------------
@router.get("/{id}/status", response_model=AgentStatusResponse)
def get_agent_status(
    id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get the agent's current status (its most recent execution's status, or 'idle')."""
    agent = _get_agent_or_404(id)
    _require_owner(agent, current_user["email"])

    recent = _executions_for_agent(id)
    latest = recent[0] if recent else None

    return AgentStatusResponse(
        agent_id=id,
        current_status=latest["status"] if latest else "idle",
        latest_execution_id=latest["id"] if latest else None,
        checked_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# GET /api/v1/agents/{id}/history
# ---------------------------------------------------------------------------
@router.get("/{id}/history", response_model=ExecutionHistoryResponse)
def get_agent_history(
    id: str,
    current_user: dict = Depends(get_current_user),
):
    """List all past executions for an agent, most recent first."""
    agent = _get_agent_or_404(id)
    _require_owner(agent, current_user["email"])

    items = _executions_for_agent(id)
    return ExecutionHistoryResponse(total=len(items), items=items)


# ---------------------------------------------------------------------------
# POST /api/v1/agents/{id}/retry
# ---------------------------------------------------------------------------
@router.post("/{id}/retry", response_model=ExecutionResponse, status_code=201)
def retry_agent(
    id: str,
    payload: ExecutionActionRequest,
    current_user: dict = Depends(get_current_user),
):
    """Retry a stopped/cancelled/failed execution by starting a new one with the same input."""
    agent = _get_agent_or_404(id)
    _require_owner(agent, current_user["email"])
    original = _resolve_execution(id, payload.execution_id)

    if original["status"] not in ("stopped", "cancelled", "failed"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot retry an execution in status '{original['status']}'",
        )

    execution_id = str(uuid4())
    now = datetime.now(timezone.utc)
    execution = {
        "id": execution_id,
        "agent_id": id,
        "owner_email": current_user["email"],
        "status": "running",
        "task": original["task"],
        "input": original["input"],
        "output": None,
        "error": None,
        "started_at": now,
        "ended_at": None,
        "updated_at": now,
    }
    executions_db[execution_id] = execution
    return execution


# ---------------------------------------------------------------------------
# POST /api/v1/agents/{id}/cancel
# ---------------------------------------------------------------------------
@router.post("/{id}/cancel", response_model=ExecutionResponse)
def cancel_agent(
    id: str,
    payload: ExecutionActionRequest,
    current_user: dict = Depends(get_current_user),
):
    """Cancel a running or paused execution (distinct from stop: intended for abandoning a run, not a clean halt)."""
    agent = _get_agent_or_404(id)
    _require_owner(agent, current_user["email"])
    execution = _resolve_execution(id, payload.execution_id)

    if execution["status"] not in ("running", "paused"):
        raise HTTPException(status_code=400, detail=f"Cannot cancel an execution in status '{execution['status']}'")

    now = datetime.now(timezone.utc)
    execution["status"] = "cancelled"
    execution["ended_at"] = now
    execution["updated_at"] = now
    return execution