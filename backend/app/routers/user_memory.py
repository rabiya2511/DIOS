"""
User Memory router — per-user memory profile CRUD, import, export.
Matches the User Memory section of the Memory APIs blueprint (6/6).

ASSUMPTIONS:
- Unlike Core Memory (many independent entries), this section models ONE
  memory profile per user_id — POST /memory/users/{id} creates it, PATCH
  updates it, GET/DELETE read/remove it. This matches the blueprint's
  path shape (all four verbs share the same /{id} path, no separate
  list-vs-create distinction).
- Scoped by "managed_by" = the CALLER, not by the target user_id's own
  account — i.e. each caller has their own private set of memory
  profiles they've recorded about various user_ids (e.g. an assistant's
  notes about users it has interacted with), not a shared/global store
  keyed purely by user_id. This avoids one account being able to
  read/overwrite another account's memory data by guessing a user_id.
  If you actually want a single shared profile per user_id across all
  callers, that's a different (simpler but less safe) design — let me
  know if you'd rather have that instead.
- POST /memory/users/{id} is an UPSERT: calling it again for the same
  user_id replaces the existing profile rather than erroring.
- POST /memory/users/export returns all of the caller's own profiles
  (no filtering) as a JSON list — it does not produce a downloadable
  file, just a JSON response with everything in it.

*** ROUTING NOTE ***
/import and /export are literal, single-segment paths under
/api/v1/memory/users — the same shape as this router's own dynamic
GET/POST/PATCH/DELETE /{id}. Both literal routes are registered BEFORE
the /{id} routes below, so FastAPI doesn't match "import"/"export" as a
user_id value. This router's prefix (/api/v1/memory/users) is 2 segments
longer than core_memory.py's prefix (/api/v1/memory), so there's no
cross-router collision with core_memory.py's own "" / "/archive" / "/{id}"
routes either.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.user_memory import (
    UserMemoryUpsertRequest,
    UserMemoryOut,
    UserMemoryImportRequest,
    UserMemoryImportResponse,
    UserMemoryExportResponse,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/memory/users", tags=["User Memory"])

# managed_by_email -> {user_id: {user_id, content, memory_type, managed_by, created_at, updated_at}}
user_memory_db: dict[str, dict[str, dict]] = {}


def _get_profiles(managed_by: str) -> dict[str, dict]:
    return user_memory_db.setdefault(managed_by, {})


# ─── Literal-path routes MUST come before any /{id} routes below ───

@router.post("/import", response_model=UserMemoryImportResponse, status_code=201)
def import_user_memory(data: UserMemoryImportRequest, current_user: dict = Depends(get_current_user)):
    email = current_user["email"]
    profiles = _get_profiles(email)
    now = datetime.now(timezone.utc)
    imported: list[dict] = []
    for entry in data.entries:
        existing = profiles.get(entry.user_id)
        created_at = existing["created_at"] if existing else now
        profiles[entry.user_id] = {
            "user_id": entry.user_id,
            "content": entry.content,
            "memory_type": entry.memory_type,
            "managed_by": email,
            "created_at": created_at,
            "updated_at": now,
        }
        imported.append(profiles[entry.user_id])
    return UserMemoryImportResponse(imported_count=len(imported), profiles=imported)


@router.post("/export", response_model=UserMemoryExportResponse)
def export_user_memory(current_user: dict = Depends(get_current_user)):
    profiles = _get_profiles(current_user["email"])
    return UserMemoryExportResponse(profiles=list(profiles.values()))


# ─── Dynamic /{id} routes come LAST ───

@router.get("/{id}", response_model=UserMemoryOut)
def get_user_memory(id: str, current_user: dict = Depends(get_current_user)):
    profiles = _get_profiles(current_user["email"])
    profile = profiles.get(id)
    if not profile:
        raise HTTPException(status_code=404, detail="User memory profile not found")
    return profile


@router.post("/{id}", response_model=UserMemoryOut, status_code=201)
def create_user_memory(id: str, data: UserMemoryUpsertRequest, current_user: dict = Depends(get_current_user)):
    email = current_user["email"]
    profiles = _get_profiles(email)
    now = datetime.now(timezone.utc)
    existing = profiles.get(id)
    profiles[id] = {
        "user_id": id,
        "content": data.content,
        "memory_type": data.memory_type,
        "managed_by": email,
        "created_at": existing["created_at"] if existing else now,
        "updated_at": now,
    }
    return profiles[id]


@router.patch("/{id}", response_model=UserMemoryOut)
def update_user_memory(id: str, data: UserMemoryUpsertRequest, current_user: dict = Depends(get_current_user)):
    profiles = _get_profiles(current_user["email"])
    profile = profiles.get(id)
    if not profile:
        raise HTTPException(status_code=404, detail="User memory profile not found")
    profile["content"] = data.content
    profile["memory_type"] = data.memory_type
    profile["updated_at"] = datetime.now(timezone.utc)
    return profile


@router.delete("/{id}", status_code=204)
def delete_user_memory(id: str, current_user: dict = Depends(get_current_user)):
    profiles = _get_profiles(current_user["email"])
    if id not in profiles:
        raise HTTPException(status_code=404, detail="User memory profile not found")
    del profiles[id]
    return None