"""
Workflows router — CRUD, run, clone, history, export.
Matches the Workflows section of the Agents & Planning APIs blueprint
(8/8). Only the workflow owner can update/delete/run/clone/export
their own workflow — same ownership model as agent_lifecycle.py /
planning.py / tasks.py / tools.py / reasoning.py. Note: like Tasks,
the blueprint has no GET /workflows/{id} — only GET /workflows (list)
and GET /workflows/history.

Literal-path routes (/run, /clone, /history, /export) MUST come
before the dynamic /{id} routes below — same ordering rule as
agent_lifecycle.py / planning.py / tasks.py / tools.py.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.workflows import (
    WorkflowCreateRequest,
    WorkflowUpdateRequest,
    WorkflowResponse,
    WorkflowListResponse,
    WorkflowIdBodyRequest,
    WorkflowCloneRequest,
    WorkflowStepResult,
    WorkflowRunResponse,
    WorkflowHistoryListResponse,
    WorkflowExportResponse,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/workflows", tags=["Workflows"])

# id -> {id, owner_email, name, description, steps, status, config, created_at, updated_at}
workflows_db: dict[str, dict] = {}

# run_id -> {run_id, workflow_id, owner_email, status, step_results, started_at, completed_at}
workflow_history_db: dict[str, dict] = {}


def _get_workflow_or_404(workflow_id: str) -> dict:
    workflow = workflows_db.get(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow


def _require_owner(workflow: dict, email: str):
    if workflow["owner_email"] != email:
        raise HTTPException(status_code=403, detail="Only the workflow owner can perform this action")


@router.post("", response_model=WorkflowResponse, status_code=201)
def create_workflow(
    data: WorkflowCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    workflow_id = str(uuid4())
    now = datetime.now(timezone.utc)
    workflows_db[workflow_id] = {
        "id": workflow_id,
        "owner_email": current_user["email"],
        "name": data.name,
        "description": data.description,
        "steps": [s.model_dump() for s in data.steps],
        "status": "draft",
        "config": data.config,
        "created_at": now,
        "updated_at": now,
    }
    return workflows_db[workflow_id]


@router.get("", response_model=WorkflowListResponse)
def list_workflows(current_user: dict = Depends(get_current_user)):
    items = [w for w in workflows_db.values() if w["owner_email"] == current_user["email"]]
    return WorkflowListResponse(total=len(items), items=items)


# ─── Literal-path routes MUST come before any /{id} routes below ───

@router.post("/run", response_model=WorkflowRunResponse, status_code=201)
def run_workflow(
    data: WorkflowIdBodyRequest,
    current_user: dict = Depends(get_current_user),
):
    workflow = _get_workflow_or_404(data.workflow_id)
    _require_owner(workflow, current_user["email"])

    if workflow["status"] == "archived":
        raise HTTPException(status_code=400, detail="Archived workflows cannot be run")

    started_at = datetime.now(timezone.utc)
    step_results: list[WorkflowStepResult] = []
    overall_status: str = "completed"

    for step in sorted(workflow["steps"], key=lambda s: s["order"]):
        step_started = datetime.now(timezone.utc)
        has_executor = any([step.get("plan_id"), step.get("agent_id"), step.get("tool_name")])
        outcome = "success" if has_executor and step["name"].strip() else "failed"
        step_completed = datetime.now(timezone.utc)

        if outcome == "failed":
            overall_status = "failed"

        step_results.append(
            WorkflowStepResult(
                order=step["order"],
                name=step["name"],
                outcome=outcome,
                output=f"Executed step '{step['name']}'" if outcome == "success" else None,
                started_at=step_started,
                completed_at=step_completed,
            )
        )

    completed_at = datetime.now(timezone.utc)
    if workflow["status"] == "draft":
        workflow["status"] = "active"
    workflow["updated_at"] = completed_at

    run_id = str(uuid4())
    workflow_history_db[run_id] = {
        "run_id": run_id,
        "workflow_id": workflow["id"],
        "owner_email": current_user["email"],
        "status": overall_status,
        "step_results": [r.model_dump() for r in step_results],
        "started_at": started_at,
        "completed_at": completed_at,
    }

    return WorkflowRunResponse(
        run_id=run_id,
        workflow_id=workflow["id"],
        status=overall_status,
        step_results=step_results,
        started_at=started_at,
        completed_at=completed_at,
    )


@router.post("/clone", response_model=WorkflowResponse, status_code=201)
def clone_workflow(
    data: WorkflowCloneRequest,
    current_user: dict = Depends(get_current_user),
):
    original = _get_workflow_or_404(data.workflow_id)
    _require_owner(original, current_user["email"])

    new_id = str(uuid4())
    now = datetime.now(timezone.utc)
    workflows_db[new_id] = {
        "id": new_id,
        "owner_email": current_user["email"],
        "name": data.new_name or f"{original['name']} (copy)",
        "description": original["description"],
        "steps": [dict(s) for s in original["steps"]],
        "status": "draft",
        "config": dict(original["config"]),
        "created_at": now,
        "updated_at": now,
    }
    return workflows_db[new_id]


@router.get("/history", response_model=WorkflowHistoryListResponse)
def get_workflow_history(
    workflow_id: str | None = None,
    current_user: dict = Depends(get_current_user),
):
    items = [
        h for h in workflow_history_db.values()
        if h["owner_email"] == current_user["email"] and (workflow_id is None or h["workflow_id"] == workflow_id)
    ]
    items.sort(key=lambda h: h["started_at"], reverse=True)
    return WorkflowHistoryListResponse(total=len(items), items=items)


@router.post("/export", response_model=WorkflowExportResponse)
def export_workflow(
    data: WorkflowIdBodyRequest,
    current_user: dict = Depends(get_current_user),
):
    workflow = _get_workflow_or_404(data.workflow_id)
    _require_owner(workflow, current_user["email"])

    return WorkflowExportResponse(
        workflow_id=workflow["id"],
        name=workflow["name"],
        description=workflow["description"],
        steps=workflow["steps"],
        config=workflow["config"],
        exported_at=datetime.now(timezone.utc),
        format="json",
    )


# ─── Dynamic /{id} routes come LAST ───

@router.patch("/{id}", response_model=WorkflowResponse)
def update_workflow(
    id: str,
    data: WorkflowUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    workflow = _get_workflow_or_404(id)
    _require_owner(workflow, current_user["email"])

    update_data = data.model_dump(exclude_unset=True)
    if "steps" in update_data and update_data["steps"] is not None:
        update_data["steps"] = [s if isinstance(s, dict) else s.model_dump() for s in update_data["steps"]]
    workflow.update(update_data)
    workflow["updated_at"] = datetime.now(timezone.utc)
    return workflow


@router.delete("/{id}", status_code=204)
def delete_workflow(id: str, current_user: dict = Depends(get_current_user)):
    workflow = _get_workflow_or_404(id)
    _require_owner(workflow, current_user["email"])
    del workflows_db[id]
    return None