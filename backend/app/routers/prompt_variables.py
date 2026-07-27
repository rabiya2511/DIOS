"""
Variables & Context router — prompt variables CRUD, context build,
get, update, clear. Matches the Variables & Context section of the
Prompt Management APIs blueprint (8/8).
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.prompt_variables import (
    PromptVariableCreateRequest,
    PromptVariableUpdateRequest,
    PromptVariableResponse,
    ContextBuildResponse,
    ContextResponse,
    ContextUpdateRequest,
    ContextDeleteResponse,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1", tags=["Variables & Context"])

# id -> {id, owner_email, name, value, description, created_at, updated_at}
prompt_variables_db: dict[str, dict] = {}

# email -> {assembled_text, variables_used, updated_at}
context_db: dict[str, dict] = {}


def _get_owned_variable(id: str, email: str) -> dict:
    var = prompt_variables_db.get(id)
    if not var or var["owner_email"] != email:
        raise HTTPException(status_code=404, detail="Prompt variable not found")
    return var


@router.get("/prompt-variables", response_model=list[PromptVariableResponse])
def list_variables(current_user: dict = Depends(get_current_user)):
    return [v for v in prompt_variables_db.values() if v["owner_email"] == current_user["email"]]


@router.post("/prompt-variables", response_model=PromptVariableResponse, status_code=201)
def create_variable(
    data: PromptVariableCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    var_id = str(uuid4())
    now = datetime.now(timezone.utc)
    prompt_variables_db[var_id] = {
        "id": var_id,
        "owner_email": current_user["email"],
        "name": data.name,
        "value": data.value,
        "description": data.description,
        "created_at": now,
        "updated_at": now,
    }
    return prompt_variables_db[var_id]


@router.patch("/prompt-variables/{id}", response_model=PromptVariableResponse)
def update_variable(
    id: str,
    data: PromptVariableUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    var = _get_owned_variable(id, current_user["email"])
    if data.value is not None:
        var["value"] = data.value
    if data.description is not None:
        var["description"] = data.description
    var["updated_at"] = datetime.now(timezone.utc)
    return var


@router.delete("/prompt-variables/{id}", status_code=204)
def delete_variable(id: str, current_user: dict = Depends(get_current_user)):
    _get_owned_variable(id, current_user["email"])
    del prompt_variables_db[id]
    return None


@router.post("/prompt-context/build", response_model=ContextBuildResponse)
def build_context(current_user: dict = Depends(get_current_user)):
    email = current_user["email"]
    variables = [v for v in prompt_variables_db.values() if v["owner_email"] == email]
    lines = [f"{v['name']}: {v['value']}" for v in variables]
    now = datetime.now(timezone.utc)
    context_db[email] = {
        "assembled_text": "\n".join(lines),
        "variables_used": [v["name"] for v in variables],
        "updated_at": now,
    }
    return context_db[email]


@router.get("/prompt-context", response_model=ContextResponse)
def get_context(current_user: dict = Depends(get_current_user)):
    email = current_user["email"]
    ctx = context_db.get(email)
    if not ctx:
        return ContextResponse(assembled_text="", variables_used=[], updated_at=None)
    return ctx


@router.patch("/prompt-context", response_model=ContextResponse)
def update_context(
    data: ContextUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    email = current_user["email"]
    ctx = context_db.setdefault(
        email, {"assembled_text": "", "variables_used": [], "updated_at": None}
    )
    extra_lines = [f"{k}: {v}" for k, v in data.extra.items()]
    if extra_lines:
        combined = "\n".join(filter(None, [ctx["assembled_text"], *extra_lines]))
        ctx["assembled_text"] = combined
    ctx["updated_at"] = datetime.now(timezone.utc)
    return ctx


@router.delete("/prompt-context", response_model=ContextDeleteResponse)
def delete_context(current_user: dict = Depends(get_current_user)):
    email = current_user["email"]
    existed = email in context_db
    context_db.pop(email, None)
    return ContextDeleteResponse(cleared=existed)