"""
Schemas for the Inference group of the Model Management APIs
blueprint.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Literal, Union
from pydantic import BaseModel, EmailStr, Field

InferenceJobStatus = Literal["queued", "processing", "completed", "failed"]
InferenceJobType = Literal["video", "batch"]


# ---------- Shared ----------

class UsageInfo(BaseModel):
    prompt_tokens: int
    completion_tokens: int = 0
    total_tokens: int


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


# ---------- Chat ----------

class ChatRequest(BaseModel):
    model_id: str
    messages: List[ChatMessage] = Field(..., min_length=1)
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(512, gt=0)


class ChatChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: Literal["stop", "length"]


class ChatResponse(BaseModel):
    id: str
    model_id: str
    owner_email: EmailStr
    choices: List[ChatChoice]
    usage: UsageInfo
    created_at: datetime


# ---------- Completion ----------

class CompletionRequest(BaseModel):
    model_id: str
    prompt: str
    max_tokens: Optional[int] = Field(256, gt=0)
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0)


class CompletionResponse(BaseModel):
    id: str
    model_id: str
    owner_email: EmailStr
    text: str
    finish_reason: Literal["stop", "length"]
    usage: UsageInfo
    created_at: datetime


# ---------- Embedding ----------

class EmbeddingRequest(BaseModel):
    model_id: str
    input: Union[str, List[str]]


class EmbeddingResponse(BaseModel):
    id: str
    model_id: str
    owner_email: EmailStr
    embeddings: List[List[float]]
    dimensions: int
    usage: UsageInfo
    created_at: datetime


# ---------- Image ----------

class ImageRequest(BaseModel):
    model_id: str
    prompt: str
    n: int = Field(1, ge=1, le=4)
    size: Literal["256x256", "512x512", "1024x1024"] = "1024x1024"


class ImageItem(BaseModel):
    url: str
    revised_prompt: Optional[str] = None


class ImageResponse(BaseModel):
    id: str
    model_id: str
    owner_email: EmailStr
    images: List[ImageItem]
    created_at: datetime


# ---------- Audio ----------

class AudioRequest(BaseModel):
    model_id: str
    text: str
    voice: Optional[str] = "default"
    format: Literal["mp3", "wav", "ogg"] = "mp3"


class AudioResponse(BaseModel):
    id: str
    model_id: str
    owner_email: EmailStr
    audio_url: str
    duration_seconds: float
    format: str
    created_at: datetime


# ---------- Video (async job) ----------

class VideoRequest(BaseModel):
    model_id: str
    prompt: str
    duration_seconds: int = Field(5, ge=1, le=60)
    resolution: Literal["480p", "720p", "1080p"] = "720p"


class VideoJobResponse(BaseModel):
    id: str
    type: Literal["video"] = "video"
    owner_email: EmailStr
    model_id: str
    status: InferenceJobStatus
    video_url: Optional[str] = None
    config: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


# ---------- Batch (async job) ----------

class BatchRequestItem(BaseModel):
    custom_id: str
    task_type: Literal["chat", "completion", "embedding"]
    payload: Dict[str, Any]


class BatchRequest(BaseModel):
    model_id: str
    requests: List[BatchRequestItem] = Field(..., min_length=1)
    config: Dict[str, Any] = Field(default_factory=dict)


class BatchJobResponse(BaseModel):
    id: str
    type: Literal["batch"] = "batch"
    owner_email: EmailStr
    model_id: str
    status: InferenceJobStatus
    request_count: int
    results: Optional[List[Dict[str, Any]]] = None
    config: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


# ---------- Jobs listing (video + batch) ----------

class InferenceJobEntry(BaseModel):
    id: str
    type: InferenceJobType
    model_id: str
    status: InferenceJobStatus
    created_at: datetime
    updated_at: datetime


class InferenceJobListResponse(BaseModel):
    total: int
    items: List[InferenceJobEntry]