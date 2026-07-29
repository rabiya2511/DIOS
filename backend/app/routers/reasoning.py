"""
Reasoning router — start, step, reflect, evaluate, explain, logs,
reset, metrics.
Matches the Reasoning section of the Agents & Planning APIs blueprint
(8/8). Only the session owner can step/reflect/evaluate/explain/reset
their own session — same ownership model as agent_lifecycle.py /
planning.py / tasks.py / tools.py.

Note: unlike the other groups, the blueprint defines NO /{id} routes
here — every operation addresses a session via a session_id in the
request body (start/step/reflect/reset) or query string (logs), so
there's no literal-path-vs-dynamic-path ordering concern in this file.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.reasoning import (
    ReasoningStartRequest,
    ReasoningSessionResponse,
    ReasoningSessionIdBodyRequest,
    ReasoningStepRequest,
    ReasoningReflectRequest,
    ReasoningEvaluateResponse,
    ReasoningExplainResponse,
    ReasoningLogEntry,
    ReasoningLogListResponse,
    ReasoningMetricsResponse,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/reasoning", tags=["Reasoning"])

# id -> {id, owner_email, goal, agent_id, status, steps, reset_count, context, created_at, updated_at}
reasoning_sessions_db: dict[str, dict] = {}


def _get_session_or_404(session_id: str) -> dict:
    session = reasoning_sessions_db.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Reasoning session not found")
    return session


def _require_owner(session: dict, email: str):
    if session["owner_email"] != email:
        raise HTTPException(status_code=403, detail="Only the session owner can perform this action")


def _require_active(session: dict):
    if session["status"] != "active":
        raise HTTPException(status_code=400, detail=f"Session is {session['status']}, not active")


@router.post("/start", response_model=ReasoningSessionResponse, status_code=201)
def start_reasoning(
    data: ReasoningStartRequest,
    current_user: dict = Depends(get_current_user),
):
    session_id = str(uuid4())
    now = datetime.now(timezone.utc)
    reasoning_sessions_db[session_id] = {
        "id": session_id,
        "owner_email": current_user["email"],
        "goal": data.goal,
        "agent_id": data.agent_id,
        "status": "active",
        "steps": [],
        "reset_count": 0,
        "context": data.context,
        "created_at": now,
        "updated_at": now,
    }
    return reasoning_sessions_db[session_id]


@router.post("/step", response_model=ReasoningSessionResponse)
def add_reasoning_step(
    data: ReasoningStepRequest,
    current_user: dict = Depends(get_current_user),
):
    session = _get_session_or_404(data.session_id)
    _require_owner(session, current_user["email"])
    _require_active(session)

    session["steps"].append({
        "step_number": len(session["steps"]) + 1,
        "step_type": data.step_type,
        "content": data.content,
        "created_at": datetime.now(timezone.utc),
    })
    session["updated_at"] = datetime.now(timezone.utc)
    return session


@router.post("/reflect", response_model=ReasoningSessionResponse)
def add_reflection(
    data: ReasoningReflectRequest,
    current_user: dict = Depends(get_current_user),
):
    """Same as /step but the step_type is always forced to 'reflection'."""
    session = _get_session_or_404(data.session_id)
    _require_owner(session, current_user["email"])
    _require_active(session)

    session["steps"].append({
        "step_number": len(session["steps"]) + 1,
        "step_type": "reflection",
        "content": data.content,
        "created_at": datetime.now(timezone.utc),
    })
    session["updated_at"] = datetime.now(timezone.utc)
    return session


@router.post("/evaluate", response_model=ReasoningEvaluateResponse)
def evaluate_reasoning(
    data: ReasoningSessionIdBodyRequest,
    current_user: dict = Depends(get_current_user),
):
    """Read-only judgment of progress so far — does not mutate the session."""
    session = _get_session_or_404(data.session_id)
    _require_owner(session, current_user["email"])

    step_count = len(session["steps"])
    if step_count == 0:
        verdict, notes = "stuck", "No reasoning steps recorded yet"
    elif step_count < 3:
        verdict, notes = "needs_more_steps", f"Only {step_count} step(s) so far — keep reasoning"
    else:
        verdict, notes = "on_track", f"{step_count} steps recorded, reasoning is progressing"

    return ReasoningEvaluateResponse(
        session_id=session["id"],
        step_count=step_count,
        verdict=verdict,
        notes=notes,
        evaluated_at=datetime.now(timezone.utc),
    )


@router.post("/explain", response_model=ReasoningExplainResponse)
def explain_reasoning(
    data: ReasoningSessionIdBodyRequest,
    current_user: dict = Depends(get_current_user),
):
    """Read-only human-readable walkthrough of the chain so far."""
    session = _get_session_or_404(data.session_id)
    _require_owner(session, current_user["email"])

    if not session["steps"]:
        explanation = "No reasoning steps have been recorded for this session yet."
    else:
        lines = [
            f"Step {s['step_number']} ({s['step_type']}): {s['content']}"
            for s in session["steps"]
        ]
        explanation = f"Goal: {session['goal']}\n" + "\n".join(lines)

    return ReasoningExplainResponse(
        session_id=session["id"],
        explanation=explanation,
        explained_at=datetime.now(timezone.utc),
    )


@router.get("/logs", response_model=ReasoningLogListResponse)
def get_reasoning_logs(
    session_id: str | None = None,
    current_user: dict = Depends(get_current_user),
):
    items: list[ReasoningLogEntry] = []
    for session in reasoning_sessions_db.values():
        if session["owner_email"] != current_user["email"]:
            continue
        if session_id is not None and session["id"] != session_id:
            continue
        for step in session["steps"]:
            items.append(ReasoningLogEntry(session_id=session["id"], **step))

    items.sort(key=lambda e: e.created_at)
    return ReasoningLogListResponse(total=len(items), items=items)


@router.post("/reset", response_model=ReasoningSessionResponse)
def reset_reasoning(
    data: ReasoningSessionIdBodyRequest,
    current_user: dict = Depends(get_current_user),
):
    session = _get_session_or_404(data.session_id)
    _require_owner(session, current_user["email"])

    session["steps"] = []
    session["reset_count"] += 1
    session["status"] = "active"
    session["updated_at"] = datetime.now(timezone.utc)
    return session


@router.get("/metrics", response_model=ReasoningMetricsResponse)
def get_reasoning_metrics(current_user: dict = Depends(get_current_user)):
    sessions = [s for s in reasoning_sessions_db.values() if s["owner_email"] == current_user["email"]]
    total_sessions = len(sessions)
    active_sessions = sum(1 for s in sessions if s["status"] == "active")
    completed_sessions = sum(1 for s in sessions if s["status"] == "completed")
    total_steps = sum(len(s["steps"]) for s in sessions)
    avg_steps_per_session = round(total_steps / total_sessions, 2) if total_sessions else 0.0

    return ReasoningMetricsResponse(
        total_sessions=total_sessions,
        active_sessions=active_sessions,
        completed_sessions=completed_sessions,
        total_steps=total_steps,
        avg_steps_per_session=avg_steps_per_session,
    )