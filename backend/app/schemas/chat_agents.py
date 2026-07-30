"""
Chat Agents router — agent create/run/stop/status/tool/planner/tasks/history.
Matches the Agents section of the AI Chat APIs blueprint (8/8).

IMPORTANT — READ BEFORE RELYING ON ANY RESULT FROM THIS ROUTER:
This is a SIMULATED agent system, same spirit as chat_reasoning_tools.py.
There is NO real autonomous execution anywhere here:
  - POST /chat/agent/run does not actually run anything — it flips a
    status flag, generates a small stub task list, and logs a history
    entry. No loop, no model calls, no real tool invocations happen.
  - POST /chat/agent/tool does NOT actually call any tool (no code
    execution, no HTTP requests, no file/DB access) — it logs the
    requested tool name/input and returns a canned "simulated" result
    string, deliberately never touching tool_input's contents beyond
    logging it. This mirrors the safety approach in
    chat_reasoning_tools.py's /python and /webhook stubs.
  - POST /chat/agent/planner does not call any planning model — it
    splits the agent's goal text into up to 3 naive steps using simple
    string splitting.
This is enough to exercise the full API contract (create, run lifecycle,
status, task list, history log) but represents NO real agentic behavior.
Wire in a real orchestration/tool-calling system before using this for
anything beyond API-contract testing.

Only the agent's owner can run/stop/query/tool-call/plan an agent.

No route-ordering concerns: every path here (/chat/agent, /chat/agent/run,
/chat/agent/stop, /chat/agent/status, /chat/agent/tool,
/chat/agent/planner, /chat/agent/tasks, /chat/agent/history) is a flat,
distinct, literal path — there is no dynamic /chat/agent/{id}, so nothing
here can be swallowed by (or swallow) another router's /chat/{id} route.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.chat_agents import (
    AgentCreateRequest,
    AgentOut,
    AgentIdRequest,
    AgentRunResponse,
    AgentStopResponse,
    AgentStatusResponse,
    AgentToolRequest,
    AgentToolResponse,
    AgentPlannerResponse,
    AgentTasksResponse,
    AgentTaskOut,
    AgentHistoryResponse,
    AgentHistoryEntry,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/chat", tags=["Chat Agents"])

# id -> {id, chat_id, name, goal, status, owner_email, created_at}
agents_db: dict[str, dict] = {}

# agent_id -> active run_id (or None)
agent_active_run_db: dict[str, str | None] = {}

# agent_id -> [{id, description, status, created_at}]
agent_tasks_db: dict[str, list[dict]] = {}

# agent_id -> [{id, agent_id, event, detail, timestamp}]
agent_history_db: dict[str, list[dict]] = {}


def _get_agent_or_404(agent_id: str) -> dict:
    agent = agents_db.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


def _require_owner(agent: dict, email: str):
    if agent["owner_email"] != email:
        raise HTTPException(status_code=403, detail="Only the agent owner can perform this action")


def _log_history(agent_id: str, event: str, detail: str):
    agent_history_db.setdefault(agent_id, []).append({
        "id": str(uuid4()),
        "agent_id": agent_id,
        "event": event,
        "detail": detail,
        "timestamp": datetime.now(timezone.utc),
    })


@router.post("/agent", response_model=AgentOut, status_code=201)
def create_agent(data: AgentCreateRequest, current_user: dict = Depends(get_current_user)):
    agent_id = str(uuid4())
    now = datetime.now(timezone.utc)
    agents_db[agent_id] = {
        "id": agent_id,
        "chat_id": data.chat_id,
        "name": data.name,
        "goal": data.goal,
        "status": "idle",
        "owner_email": current_user["email"],
        "created_at": now,
    }
    agent_tasks_db[agent_id] = []
    agent_active_run_db[agent_id] = None
    _log_history(agent_id, "created", f"Agent '{data.name}' created with goal: {data.goal}")
    return agents_db[agent_id]


@router.post("/agent/run", response_model=AgentRunResponse)
def run_agent(data: AgentIdRequest, current_user: dict = Depends(get_current_user)):
    agent = _get_agent_or_404(data.agent_id)
    _require_owner(agent, current_user["email"])

    run_id = str(uuid4())
    now = datetime.now(timezone.utc)
    agent["status"] = "running"
    agent_active_run_db[data.agent_id] = run_id

    # STUB: naive goal decomposition, not a real planner. See module docstring.
    if not agent_tasks_db.get(data.agent_id):
        words = agent["goal"].split()
        chunk_size = max(1, len(words) // 3 or 1)
        chunks = [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)][:3]
        agent_tasks_db[data.agent_id] = [
            {"id": str(uuid4()), "description": f"Work on: {chunk}", "status": "pending", "created_at": now}
            for chunk in chunks
        ]

    _log_history(data.agent_id, "run_started", f"Run {run_id} started")
    return AgentRunResponse(run_id=run_id, agent_id=data.agent_id, status="running", started_at=now)


@router.post("/agent/stop", response_model=AgentStopResponse)
def stop_agent(data: AgentIdRequest, current_user: dict = Depends(get_current_user)):
    agent = _get_agent_or_404(data.agent_id)
    _require_owner(agent, current_user["email"])

    if agent["status"] != "running":
        raise HTTPException(status_code=400, detail="Agent is not currently running")

    now = datetime.now(timezone.utc)
    agent["status"] = "stopped"
    run_id = agent_active_run_db.get(data.agent_id)
    agent_active_run_db[data.agent_id] = None
    _log_history(data.agent_id, "run_stopped", f"Run {run_id} stopped")
    return AgentStopResponse(agent_id=data.agent_id, status="stopped", stopped_at=now)


@router.post("/agent/status", response_model=AgentStatusResponse)
def get_agent_status(data: AgentIdRequest, current_user: dict = Depends(get_current_user)):
    agent = _get_agent_or_404(data.agent_id)
    _require_owner(agent, current_user["email"])

    tasks = agent_tasks_db.get(data.agent_id, [])
    completed = sum(1 for t in tasks if t["status"] == "completed")
    return AgentStatusResponse(
        agent_id=data.agent_id,
        status=agent["status"],
        active_run_id=agent_active_run_db.get(data.agent_id),
        task_count=len(tasks),
        completed_task_count=completed,
    )


@router.post("/agent/tool", response_model=AgentToolResponse, status_code=201)
def agent_tool_call(data: AgentToolRequest, current_user: dict = Depends(get_current_user)):
    agent = _get_agent_or_404(data.agent_id)
    _require_owner(agent, current_user["email"])

    # STUB — deliberately does not execute data.tool_input in any way.
    # See module docstring for why (mirrors chat_reasoning_tools.py safety approach).
    result = f"[simulated] Tool '{data.tool_name}' invoked — no real execution performed."
    now = datetime.now(timezone.utc)
    tool_call_id = str(uuid4())
    _log_history(data.agent_id, "tool_call", f"Tool '{data.tool_name}' invoked (simulated)")
    return AgentToolResponse(id=tool_call_id, agent_id=data.agent_id, tool_name=data.tool_name, result=result, created_at=now)


@router.post("/agent/planner", response_model=AgentPlannerResponse)
def agent_planner(data: AgentIdRequest, current_user: dict = Depends(get_current_user)):
    agent = _get_agent_or_404(data.agent_id)
    _require_owner(agent, current_user["email"])

    # STUB — naive text splitting, not a real planning model. See module docstring.
    words = agent["goal"].split()
    chunk_size = max(1, len(words) // 3 or 1)
    steps = [f"Step: {' '.join(words[i:i + chunk_size])}" for i in range(0, len(words), chunk_size)][:3]
    if not steps:
        steps = ["Step: (no goal text provided)"]

    now = datetime.now(timezone.utc)
    _log_history(data.agent_id, "planned", f"Generated {len(steps)} plan steps")
    return AgentPlannerResponse(agent_id=data.agent_id, plan_steps=steps, created_at=now)


@router.post("/agent/tasks", response_model=AgentTasksResponse)
def list_agent_tasks(data: AgentIdRequest, current_user: dict = Depends(get_current_user)):
    agent = _get_agent_or_404(data.agent_id)
    _require_owner(agent, current_user["email"])
    tasks = agent_tasks_db.get(data.agent_id, [])
    return AgentTasksResponse(agent_id=data.agent_id, tasks=[AgentTaskOut(**t) for t in tasks])


@router.post("/agent/history", response_model=AgentHistoryResponse)
def get_agent_history(data: AgentIdRequest, current_user: dict = Depends(get_current_user)):
    agent = _get_agent_or_404(data.agent_id)
    _require_owner(agent, current_user["email"])
    history = agent_history_db.get(data.agent_id, [])
    history_sorted = sorted(history, key=lambda h: h["timestamp"], reverse=True)
    return AgentHistoryResponse(agent_id=data.agent_id, history=[AgentHistoryEntry(**h) for h in history_sorted])