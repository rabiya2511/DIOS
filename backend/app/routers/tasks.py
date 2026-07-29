"""
Tasks router — CRUD, assign, complete, retry, queue.
Matches the Tasks section of the Agents & Planning APIs blueprint
(8/8). Only the task owner can update/delete/assign/complete/retry
their own task — same ownership model as agent_lifecycle.py /
planning.py. Note: the blueprint has no GET /tasks/{id} — only
GET /tasks (list) and GET /tasks/queue.

Literal-path routes (/assign, /complete, /retry, /queue) MUST come
before the dynamic /{id} routes below — same ordering rule as
agent_lifecycle.py / planning.py.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.tasks import (
    TaskCreateRequest,
    TaskUpdateRequest,
    TaskResponse,
    TaskListResponse,
    TaskIdBodyRequest,
    TaskAssignRequest,
    TaskCompleteRequest,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/tasks", tags=["Tasks"])

# id -> {id, owner_email, title, description, plan_id, agent_id, priority,
#        status, result, retry_count, config, created_at, updated_at}
tasks_db: dict[str, dict] = {}


def _get_task_or_404(task_id: str) -> dict:
    task = tasks_db.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


def _require_owner(task: dict, email: str):
    if task["owner_email"] != email:
        raise HTTPException(status_code=403, detail="Only the task owner can perform this action")


@router.get("", response_model=TaskListResponse)
def list_tasks(
    status: str | None = None,
    current_user: dict = Depends(get_current_user),
):
    items = [
        t for t in tasks_db.values()
        if t["owner_email"] == current_user["email"] and (status is None or t["status"] == status)
    ]
    return TaskListResponse(total=len(items), items=items)


@router.post("", response_model=TaskResponse, status_code=201)
def create_task(
    data: TaskCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    task_id = str(uuid4())
    now = datetime.now(timezone.utc)
    tasks_db[task_id] = {
        "id": task_id,
        "owner_email": current_user["email"],
        "title": data.title,
        "description": data.description,
        "plan_id": data.plan_id,
        "agent_id": data.agent_id,
        "priority": data.priority,
        "status": "assigned" if data.agent_id else "pending",
        "result": None,
        "retry_count": 0,
        "config": data.config,
        "created_at": now,
        "updated_at": now,
    }
    return tasks_db[task_id]


# ─── Literal-path routes MUST come before any /{id} routes below ───

@router.post("/assign", response_model=TaskResponse)
def assign_task(
    data: TaskAssignRequest,
    current_user: dict = Depends(get_current_user),
):
    task = _get_task_or_404(data.task_id)
    _require_owner(task, current_user["email"])

    task["agent_id"] = data.agent_id
    task["status"] = "assigned"
    task["updated_at"] = datetime.now(timezone.utc)
    return task


@router.post("/complete", response_model=TaskResponse)
def complete_task(
    data: TaskCompleteRequest,
    current_user: dict = Depends(get_current_user),
):
    task = _get_task_or_404(data.task_id)
    _require_owner(task, current_user["email"])

    task["status"] = "completed"
    task["result"] = data.result
    task["updated_at"] = datetime.now(timezone.utc)
    return task


@router.post("/retry", response_model=TaskResponse)
def retry_task(
    data: TaskIdBodyRequest,
    current_user: dict = Depends(get_current_user),
):
    task = _get_task_or_404(data.task_id)
    _require_owner(task, current_user["email"])

    if task["status"] != "failed":
        raise HTTPException(status_code=400, detail="Only failed tasks can be retried")

    task["status"] = "assigned" if task["agent_id"] else "pending"
    task["retry_count"] += 1
    task["updated_at"] = datetime.now(timezone.utc)
    return task


@router.get("/queue", response_model=TaskListResponse)
def get_task_queue(current_user: dict = Depends(get_current_user)):
    """Tasks still waiting to run, ordered highest priority first, then oldest first."""
    items = [
        t for t in tasks_db.values()
        if t["owner_email"] == current_user["email"] and t["status"] in ("pending", "assigned")
    ]
    items.sort(key=lambda t: (-t["priority"], t["created_at"]))
    return TaskListResponse(total=len(items), items=items)


# ─── Dynamic /{id} routes come LAST ───

@router.patch("/{id}", response_model=TaskResponse)
def update_task(
    id: str,
    data: TaskUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    task = _get_task_or_404(id)
    _require_owner(task, current_user["email"])

    update_data = data.model_dump(exclude_unset=True)
    task.update(update_data)
    task["updated_at"] = datetime.now(timezone.utc)
    return task


@router.delete("/{id}", status_code=204)
def delete_task(id: str, current_user: dict = Depends(get_current_user)):
    task = _get_task_or_404(id)
    _require_owner(task, current_user["email"])
    del tasks_db[id]
    return None