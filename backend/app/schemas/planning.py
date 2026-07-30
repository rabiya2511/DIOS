"""
Planning router — CRUD, validate, simulate, execute, results.
Matches the Planning section of the Agents & Planning APIs blueprint
(8/8). Only the plan owner can read/update/delete/validate/simulate/
execute their own plan — same ownership model as agent_lifecycle.py.

Literal-path routes (/execute, /validate, /simulate, /results) MUST
come before the dynamic /{id} routes below — same ordering rule as
agent_lifecycle.py / conversations.py / fileslifecycle.py.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.planning import (
    PlanCreateRequest,
    PlanUpdateRequest,
    PlanResponse,
    PlanIdBodyRequest,
    PlanValidationIssue,
    PlanValidateResponse,
    SimulatedStepResult,
    PlanSimulateResponse,
    StepExecutionResult,
    PlanExecuteResponse,
    PlanResultResponse,
    PlanResultListResponse,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/planning", tags=["Planning"])

# id -> {id, owner_email, name, goal, description, agent_id, steps, config, status, created_at, updated_at}
plans_db: dict[str, dict] = {}

# result_id -> {result_id, plan_id, owner_email, status, step_results, started_at, completed_at}
results_db: dict[str, dict] = {}


def _get_plan_or_404(plan_id: str) -> dict:
    plan = plans_db.get(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


def _require_owner(plan: dict, email: str):
    if plan["owner_email"] != email:
        raise HTTPException(status_code=403, detail="Only the plan owner can perform this action")


def _check_plan(plan: dict) -> list[PlanValidationIssue]:
    """Shared rule-checking used by both /validate and /simulate."""
    issues: list[PlanValidationIssue] = []
    steps = plan["steps"]

    if not steps:
        issues.append(PlanValidationIssue(message="Plan has no steps"))
        return issues

    orders = [s["order"] for s in steps]
    if len(orders) != len(set(orders)):
        issues.append(PlanValidationIssue(message="Step order values must be unique"))

    for step in steps:
        if not step["description"].strip():
            issues.append(
                PlanValidationIssue(step_order=step["order"], message="Step description is empty")
            )
        if step.get("tool_name") is None and step.get("agent_id") is None:
            issues.append(
                PlanValidationIssue(
                    step_order=step["order"],
                    message="Step has neither a tool_name nor an agent_id to execute it",
                )
            )

    return issues


@router.post("/create", response_model=PlanResponse, status_code=201)
def create_plan(
    data: PlanCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    plan_id = str(uuid4())
    now = datetime.now(timezone.utc)
    plans_db[plan_id] = {
        "id": plan_id,
        "owner_email": current_user["email"],
        "name": data.name,
        "goal": data.goal,
        "description": data.description,
        "agent_id": data.agent_id,
        "steps": [s.model_dump() for s in data.steps],
        "config": data.config,
        "status": "draft",
        "created_at": now,
        "updated_at": now,
    }
    return plans_db[plan_id]


# ─── Literal-path routes MUST come before any /{id} routes below ───

@router.post("/validate", response_model=PlanValidateResponse)
def validate_plan(
    data: PlanIdBodyRequest,
    current_user: dict = Depends(get_current_user),
):
    plan = _get_plan_or_404(data.plan_id)
    _require_owner(plan, current_user["email"])

    issues = _check_plan(plan)
    plan["status"] = "invalid" if issues else "validated"
    plan["updated_at"] = datetime.now(timezone.utc)

    return PlanValidateResponse(
        plan_id=plan["id"],
        valid=not issues,
        issues=issues,
        validated_at=plan["updated_at"],
    )


@router.post("/simulate", response_model=PlanSimulateResponse)
def simulate_plan(
    data: PlanIdBodyRequest,
    current_user: dict = Depends(get_current_user),
):
    """Dry-run a plan: predicts step outcomes without invoking any real
    tools/agents and without mutating plan or result state."""
    plan = _get_plan_or_404(data.plan_id)
    _require_owner(plan, current_user["email"])

    issues = _check_plan(plan)
    invalid_orders = {i.step_order for i in issues if i.step_order is not None}

    simulated_steps = []
    for step in sorted(plan["steps"], key=lambda s: s["order"]):
        if step["order"] in invalid_orders:
            simulated_steps.append(
                SimulatedStepResult(
                    order=step["order"],
                    description=step["description"],
                    predicted_outcome="skipped",
                    predicted_output="Skipped: step failed validation",
                )
            )
        else:
            simulated_steps.append(
                SimulatedStepResult(
                    order=step["order"],
                    description=step["description"],
                    predicted_outcome="success",
                    predicted_output=f"Predicted output for step {step['order']}",
                )
            )

    failed = sum(1 for s in simulated_steps if s.predicted_outcome != "success")
    summary = (
        "All steps predicted to succeed"
        if failed == 0
        else f"{failed} of {len(simulated_steps)} step(s) predicted to fail or be skipped"
    )

    return PlanSimulateResponse(
        plan_id=plan["id"],
        simulated_at=datetime.now(timezone.utc),
        steps=simulated_steps,
        summary=summary,
    )


@router.post("/execute", response_model=PlanExecuteResponse, status_code=201)
def execute_plan(
    data: PlanIdBodyRequest,
    current_user: dict = Depends(get_current_user),
):
    plan = _get_plan_or_404(data.plan_id)
    _require_owner(plan, current_user["email"])

    started_at = datetime.now(timezone.utc)
    plan["status"] = "executing"
    plan["updated_at"] = started_at

    step_results: list[StepExecutionResult] = []
    overall_status: str = "completed"

    for step in sorted(plan["steps"], key=lambda s: s["order"]):
        step_started = datetime.now(timezone.utc)
        has_executor = step.get("tool_name") is not None or step.get("agent_id") is not None
        outcome = "success" if has_executor and step["description"].strip() else "failed"
        step_completed = datetime.now(timezone.utc)

        if outcome == "failed":
            overall_status = "failed"

        step_results.append(
            StepExecutionResult(
                order=step["order"],
                description=step["description"],
                outcome=outcome,
                output=f"Executed step {step['order']}" if outcome == "success" else None,
                started_at=step_started,
                completed_at=step_completed,
            )
        )

    completed_at = datetime.now(timezone.utc)
    plan["status"] = overall_status
    plan["updated_at"] = completed_at

    result_id = str(uuid4())
    results_db[result_id] = {
        "result_id": result_id,
        "plan_id": plan["id"],
        "owner_email": current_user["email"],
        "status": overall_status,
        "step_results": [r.model_dump() for r in step_results],
        "started_at": started_at,
        "completed_at": completed_at,
    }

    return PlanExecuteResponse(
        result_id=result_id,
        plan_id=plan["id"],
        status=overall_status,
        step_results=step_results,
        started_at=started_at,
        completed_at=completed_at,
    )


@router.get("/results", response_model=PlanResultListResponse)
def list_plan_results(
    plan_id: str | None = None,
    current_user: dict = Depends(get_current_user),
):
    items = [
        r for r in results_db.values()
        if r["owner_email"] == current_user["email"] and (plan_id is None or r["plan_id"] == plan_id)
    ]
    return PlanResultListResponse(total=len(items), items=items)


# ─── Dynamic /{id} routes come LAST ───

@router.get("/{id}", response_model=PlanResponse)
def get_plan(id: str, current_user: dict = Depends(get_current_user)):
    plan = _get_plan_or_404(id)
    _require_owner(plan, current_user["email"])
    return plan


@router.patch("/{id}", response_model=PlanResponse)
def update_plan(
    id: str,
    data: PlanUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    plan = _get_plan_or_404(id)
    _require_owner(plan, current_user["email"])

    update_data = data.model_dump(exclude_unset=True)
    if "steps" in update_data and update_data["steps"] is not None:
        update_data["steps"] = [s if isinstance(s, dict) else s.model_dump() for s in update_data["steps"]]
    plan.update(update_data)
    plan["status"] = "draft"  # edits invalidate any prior validation/execution status
    plan["updated_at"] = datetime.now(timezone.utc)
    return plan


@router.delete("/{id}", status_code=204)
def delete_plan(id: str, current_user: dict = Depends(get_current_user)):
    plan = _get_plan_or_404(id)
    _require_owner(plan, current_user["email"])
    del plans_db[id]
    return None