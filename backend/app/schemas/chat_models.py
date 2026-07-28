"""

Pydantic schemas for the Model Selection domain (AI Chat APIs

blueprint). Models are seeded at startup; per-user state (current

model, fallback, preferences) is tracked separately.

"""



from typing import Any



from pydantic import BaseModel





class ModelResponse(BaseModel):

    id: str

    name: str

    provider: str

    context_window: int

    capabilities: list[str]





class ModelSelectRequest(BaseModel):

    model_id: str





class ModelPreferencesRequest(BaseModel):

    preferences: dict[str, Any]





class ModelPreferencesResponse(BaseModel):

    preferences: dict[str, Any]





class ModelCapabilitiesResponse(BaseModel):

    model_id: str

    capabilities: list[str]





class ModelRouterRequest(BaseModel):

    task_type: str





class ModelRouterResponse(BaseModel):

    task_type: str

    recommended_model_id: str

    reason: str