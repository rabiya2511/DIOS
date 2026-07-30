"""
Embeddings router — create, update, delete, rebuild, models,
select-model, stats, batch. Matches the Embeddings section of the
Knowledge / RAG APIs blueprint (8/8). STUBBED: vectors are
deterministic fake floats, not real embedding model output.

No ordering conflicts — every path is a fixed literal string, no
dynamic {id} segments in this router (ids are passed in bodies/query).
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.embeddings import (
    EmbeddingModelResponse,
    EmbeddingCreateRequest,
    EmbeddingUpdateRequest,
    EmbeddingDeleteRequest,
    EmbeddingResponse,
    EmbeddingDeleteResponse,
    RebuildResponse,
    SelectModelRequest,
    EmbeddingStatsResponse,
    BatchEmbeddingRequest,
    BatchEmbeddingResponse,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/embeddings", tags=["Embeddings"])

# id -> {id, name, dimensions}
embedding_models_db: dict[str, dict] = {}

# id -> {id, owner_email, source_text, model_id, vector, created_at}
embeddings_db: dict[str, dict] = {}

# email -> model_id
user_embedding_model_db: dict[str, str] = {}

DEFAULT_MODEL_ID = "embed-small"


def _seed_models():
    if embedding_models_db:
        return
    for id_, name, dims in [
        ("embed-small", "Small Embedding Model", 384),
        ("embed-large", "Large Embedding Model", 1536),
    ]:
        embedding_models_db[id_] = {"id": id_, "name": name, "dimensions": dims}


_seed_models()


def _get_model_or_404(model_id: str) -> dict:
    model = embedding_models_db.get(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Embedding model not found")
    return model


def _get_selected_model_id(email: str) -> str:
    return user_embedding_model_db.get(email, DEFAULT_MODEL_ID)


def _fake_vector(text: str, dimensions: int) -> list[float]:
    # STUB: deterministic pseudo-vector derived from character codes,
    # truncated/padded to the model's declared dimensionality (capped
    # for response size — real vectors of 384/1536 dims would be huge).
    sample_len = min(dimensions, 8)
    seed = [((ord(c) % 97) / 97) for c in (text or " ")]
    vector = (seed * ((sample_len // max(len(seed), 1)) + 1))[:sample_len]
    return [round(v, 4) for v in vector]


def _get_owned_embedding(embedding_id: str, email: str) -> dict:
    emb = embeddings_db.get(embedding_id)
    if not emb or emb["owner_email"] != email:
        raise HTTPException(status_code=404, detail="Embedding not found")
    return emb


@router.get("/models", response_model=list[EmbeddingModelResponse])
def list_models():
    return list(embedding_models_db.values())


@router.post("/select-model", response_model=EmbeddingModelResponse)
def select_model(data: SelectModelRequest, current_user: dict = Depends(get_current_user)):
    model = _get_model_or_404(data.model_id)
    user_embedding_model_db[current_user["email"]] = data.model_id
    return model


@router.post("/create", response_model=EmbeddingResponse, status_code=201)
def create_embedding(data: EmbeddingCreateRequest, current_user: dict = Depends(get_current_user)):
    model_id = data.model_id or _get_selected_model_id(current_user["email"])
    model = _get_model_or_404(model_id)

    embedding_id = str(uuid4())
    now = datetime.now(timezone.utc)
    embeddings_db[embedding_id] = {
        "id": embedding_id,
        "owner_email": current_user["email"],
        "source_text": data.text,
        "model_id": model_id,
        "vector": _fake_vector(data.text, model["dimensions"]),
        "created_at": now,
    }
    return embeddings_db[embedding_id]


@router.post("/update", response_model=EmbeddingResponse)
def update_embedding(data: EmbeddingUpdateRequest, current_user: dict = Depends(get_current_user)):
    emb = _get_owned_embedding(data.embedding_id, current_user["email"])
    model = _get_model_or_404(emb["model_id"])
    emb["source_text"] = data.text
    emb["vector"] = _fake_vector(data.text, model["dimensions"])
    return emb


@router.post("/delete", response_model=EmbeddingDeleteResponse)
def delete_embedding(data: EmbeddingDeleteRequest, current_user: dict = Depends(get_current_user)):
    _get_owned_embedding(data.embedding_id, current_user["email"])
    del embeddings_db[data.embedding_id]
    return EmbeddingDeleteResponse(deleted=True)


@router.post("/rebuild", response_model=RebuildResponse)
def rebuild_embeddings(current_user: dict = Depends(get_current_user)):
    email = current_user["email"]
    owned = [e for e in embeddings_db.values() if e["owner_email"] == email]
    for emb in owned:
        model = _get_model_or_404(emb["model_id"])
        emb["vector"] = _fake_vector(emb["source_text"], model["dimensions"])
    return RebuildResponse(rebuilt_count=len(owned), completed_at=datetime.now(timezone.utc))


@router.get("/stats", response_model=EmbeddingStatsResponse)
def get_stats(current_user: dict = Depends(get_current_user)):
    email = current_user["email"]
    owned = [e for e in embeddings_db.values() if e["owner_email"] == email]
    avg_dims = sum(len(e["vector"]) for e in owned) / len(owned) if owned else 0.0
    return EmbeddingStatsResponse(
        total_embeddings=len(owned),
        current_model_id=_get_selected_model_id(email),
        average_dimensions=round(avg_dims, 2),
    )


@router.post("/batch", response_model=BatchEmbeddingResponse)
def batch_create(data: BatchEmbeddingRequest, current_user: dict = Depends(get_current_user)):
    model_id = data.model_id or _get_selected_model_id(current_user["email"])
    model = _get_model_or_404(model_id)

    created = []
    now = datetime.now(timezone.utc)
    for text in data.texts:
        embedding_id = str(uuid4())
        embeddings_db[embedding_id] = {
            "id": embedding_id,
            "owner_email": current_user["email"],
            "source_text": text,
            "model_id": model_id,
            "vector": _fake_vector(text, model["dimensions"]),
            "created_at": now,
        }
        created.append(embeddings_db[embedding_id])

    return BatchEmbeddingResponse(created=len(created), embeddings=created)