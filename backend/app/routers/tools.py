"""
Tools router — CRUD, invoke, history, authorize, test.
Matches the Tools section of the Agents & Planning APIs blueprint
(8/8). Only the tool owner can update/delete/authorize/test their
own tool — same ownership model as agent_lifecycle.py / planning.py
/ tasks.py. Invoking a tool is allowed for the owner, or for a caller
supplying an agent_id that the owner has explicitly authorized via
/tools/authorize.

Literal-path routes (/invoke, /history, /authorize, /test) MUST come
before the dynamic /{id} routes below — same ordering rule as
agent_lifecycle.py / planning.py / tasks.py.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.tools import (
    ToolRegisterRequest,
    ToolUpdateRequest,
    ToolResponse,
    ToolListResponse,
    ToolAuthorizeRequest,
    ToolInvokeRequest,
    ToolInvokeResponse,
    ToolTestRequest,
    ToolTestResponse,
    ToolHistoryListResponse,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/tools", tags=["Tools"])

# id -> {id, owner_email, name, description, tool_type, endpoint, auth_required,
#        status, authorized_agent_ids, config, created_at, updated_at}
tools_db: dict[str, dict] = {}

# invocation_id -> {invocation_id, tool_id, agent_id, invoker_email, status, params, output, invoked_at}
tool_history_db: dict[str, dict] = {}


def _get_tool_or_404(tool_id: str) -> dict:
    tool = tools_db.get(tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    return tool


def _require_owner(tool: dict, email: str):
    if tool["owner_email"] != email:
        raise HTTPException(status_code=403, detail="Only the tool owner can perform this action")


def _run_tool(tool: dict, params: dict) -> tuple[str, str | None]:
    """Stub executor — no real side effects yet. Fails if an api/webhook
    tool has no endpoint configured, succeeds otherwise."""
    if tool["tool_type"] in ("api", "webhook") and not tool["endpoint"]:
        return "failed", "No endpoint configured for this tool"
    return "success", f"Executed '{tool['name']}' with params {params}"


@router.get("", response_model=ToolListResponse)
def list_tools(current_user: dict = Depends(get_current_user)):
    items = [t for t in tools_db.values() if t["owner_email"] == current_user["email"]]
    return ToolListResponse(total=len(items), items=items)


@router.post("/register", response_model=ToolResponse, status_code=201)
def register_tool(
    data: ToolRegisterRequest,
    current_user: dict = Depends(get_current_user),
):
    tool_id = str(uuid4())
    now = datetime.now(timezone.utc)
    tools_db[tool_id] = {
        "id": tool_id,
        "owner_email": current_user["email"],
        "name": data.name,
        "description": data.description,
        "tool_type": data.tool_type,
        "endpoint": data.endpoint,
        "auth_required": data.auth_required,
        "status": "active",
        "authorized_agent_ids": [],
        "config": data.config,
        "created_at": now,
        "updated_at": now,
    }
    return tools_db[tool_id]


# ─── Literal-path routes MUST come before any /{id} routes below ───

@router.post("/authorize", response_model=ToolResponse)
def authorize_tool(
    data: ToolAuthorizeRequest,
    current_user: dict = Depends(get_current_user),
):
    tool = _get_tool_or_404(data.tool_id)
    _require_owner(tool, current_user["email"])

    if data.agent_id not in tool["authorized_agent_ids"]:
        tool["authorized_agent_ids"].append(data.agent_id)
    tool["updated_at"] = datetime.now(timezone.utc)
    return tool


@router.post("/test", response_model=ToolTestResponse)
def test_tool(
    data: ToolTestRequest,
    current_user: dict = Depends(get_current_user),
):
    """Owner-only dry run — exercises the same stub executor as /invoke
    but never writes to tool_history_db."""
    tool = _get_tool_or_404(data.tool_id)
    _require_owner(tool, current_user["email"])

    status, output = _run_tool(tool, data.params)
    return ToolTestResponse(
        tool_id=tool["id"],
        status=status,
        output=output,
        tested_at=datetime.now(timezone.utc),
    )


@router.post("/invoke", response_model=ToolInvokeResponse, status_code=201)
def invoke_tool(
    data: ToolInvokeRequest,
    current_user: dict = Depends(get_current_user),
):
    tool = _get_tool_or_404(data.tool_id)

    is_owner = tool["owner_email"] == current_user["email"]
    is_authorized_agent = data.agent_id is not None and data.agent_id in tool["authorized_agent_ids"]

    invoked_at = datetime.now(timezone.utc)

    if tool["status"] != "active":
        raise HTTPException(status_code=400, detail="Tool is disabled")

    if not is_owner and not is_authorized_agent:
        status, output = "unauthorized", "Caller is neither the tool owner nor an authorized agent"
    else:
        status, output = _run_tool(tool, data.params)

    invocation_id = str(uuid4())
    tool_history_db[invocation_id] = {
        "invocation_id": invocation_id,
        "tool_id": tool["id"],
        "agent_id": data.agent_id,
        "invoker_email": current_user["email"],
        "status": status,
        "params": data.params,
        "output": output,
        "invoked_at": invoked_at,
    }

    if status == "unauthorized":
        raise HTTPException(status_code=403, detail=output)

    return ToolInvokeResponse(
        invocation_id=invocation_id,
        tool_id=tool["id"],
        status=status,
        output=output,
        invoked_at=invoked_at,
    )


@router.get("/history", response_model=ToolHistoryListResponse)
def get_tool_history(
    tool_id: str | None = None,
    current_user: dict = Depends(get_current_user),
):
    items = [
        h for h in tool_history_db.values()
        if h["invoker_email"] == current_user["email"] and (tool_id is None or h["tool_id"] == tool_id)
    ]
    items.sort(key=lambda h: h["invoked_at"], reverse=True)
    return ToolHistoryListResponse(total=len(items), items=items)


# ─── Dynamic /{id} routes come LAST ───

@router.patch("/{id}", response_model=ToolResponse)
def update_tool(
    id: str,
    data: ToolUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    tool = _get_tool_or_404(id)
    _require_owner(tool, current_user["email"])

    update_data = data.model_dump(exclude_unset=True)
    tool.update(update_data)
    tool["updated_at"] = datetime.now(timezone.utc)
    return tool


@router.delete("/{id}", status_code=204)
def delete_tool(id: str, current_user: dict = Depends(get_current_user)):
    tool = _get_tool_or_404(id)
    _require_owner(tool, current_user["email"])
    del tools_db[id]
    return None