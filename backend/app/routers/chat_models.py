"""
Model Selection router — list models, select, switch, current,
preferences, capabilities, fallback, router. Matches the Model
Selection section of the AI Chat APIs blueprint (8/8). Models are
seeded at startup; select/switch are functionally identical (both set
the user's current model) — kept as separate endpoints per the
blueprint's naming, since some clients distinguish "pick for the
first time" from "change mid-conversation."
"""

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.chat_models import (
    ModelResponse,
    ModelSelectRequest,
    ModelPreferencesRequest,
    ModelPreferencesResponse,
    ModelCapabilitiesResponse,
    ModelRouterRequest,
    ModelRouterResponse,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1", tags=["Model Selection"])

# id -> {id, name, provider, context_window, capabilities}
models_db: dict[str, dict] = {}

# email -> {current_model_id, fallback_model_id, preferences}
user_model_state_db: dict[str, dict] = {}


def _seed_models():
    if models_db:
        return
    for id_, name, provider, window, caps in [
        ("model-fast", "Fast Model", "internal", 32000, ["text", "chat"]),
        ("model-standard", "Standard Model", "internal", 128000, ["text", "chat", "code", "vision"]),
        ("model-advanced", "Advanced Model", "internal", 200000, ["text", "chat", "code", "vision", "reasoning"]),
    ]:
        models_db[id_] = {
            "id": id_,
            "name": name,
            "provider": provider,
            "context_window": window,
            "capabilities": caps,
        }


_seed_models()

DEFAULT_MODEL_ID = "model-standard"


def _get_model_or_404(model_id: str) -> dict:
    model = models_db.get(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model


def _get_or_create_state(email: str) -> dict:
    return user_model_state_db.setdefault(
        email,
        {"current_model_id": DEFAULT_MODEL_ID, "fallback_model_id": None, "preferences": {}},
    )


@router.get("/chat/models", response_model=list[ModelResponse])
def list_models():
    return list(models_db.values())


@router.post("/chat/model/select", response_model=ModelResponse)
def select_model(data: ModelSelectRequest, current_user: dict = Depends(get_current_user)):
    _get_model_or_404(data.model_id)
    state = _get_or_create_state(current_user["email"])
    state["current_model_id"] = data.model_id
    return models_db[data.model_id]


@router.post("/chat/model/switch", response_model=ModelResponse)
def switch_model(data: ModelSelectRequest, current_user: dict = Depends(get_current_user)):
    _get_model_or_404(data.model_id)
    state = _get_or_create_state(current_user["email"])
    state["current_model_id"] = data.model_id
    return models_db[data.model_id]


@router.get("/chat/model/current", response_model=ModelResponse)
def get_current_model(current_user: dict = Depends(get_current_user)):
    state = _get_or_create_state(current_user["email"])
    return models_db[state["current_model_id"]]


@router.post("/chat/model/preferences", response_model=ModelPreferencesResponse)
def set_model_preferences(
    data: ModelPreferencesRequest,
    current_user: dict = Depends(get_current_user),
):
    state = _get_or_create_state(current_user["email"])
    state["preferences"].update(data.preferences)
    return ModelPreferencesResponse(preferences=state["preferences"])


@router.get("/chat/model/capabilities", response_model=ModelCapabilitiesResponse)
def get_model_capabilities(model_id: str):
    model = _get_model_or_404(model_id)
    return ModelCapabilitiesResponse(model_id=model_id, capabilities=model["capabilities"])


@router.post("/chat/model/fallback", response_model=ModelResponse)
def set_fallback_model(data: ModelSelectRequest, current_user: dict = Depends(get_current_user)):
    _get_model_or_404(data.model_id)
    state = _get_or_create_state(current_user["email"])
    state["fallback_model_id"] = data.model_id
    return models_db[data.model_id]


@router.post("/chat/model/router", response_model=ModelRouterResponse)
def route_task(data: ModelRouterRequest, current_user: dict = Depends(get_current_user)):
    # STUB: simple rule-based routing by task type.
    task = data.task_type.lower()
    if task in ("code", "coding", "programming"):
        model_id, reason = "model-advanced", "Advanced model recommended for code-related tasks"
    elif task in ("vision", "image"):
        model_id, reason = "model-standard", "Standard model supports vision capabilities"
    elif task in ("reasoning", "analysis"):
        model_id, reason = "model-advanced", "Advanced model recommended for complex reasoning"
    else:
        model_id, reason = "model-fast", "Fast model is sufficient for general text tasks"

    return ModelRouterResponse(task_type=data.task_type, recommended_model_id=model_id, reason=reason)