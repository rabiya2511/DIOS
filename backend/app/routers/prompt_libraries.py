"""
Prompt Libraries & Sharing router — library publish/browse, share/unshare,
favorite/unfavorite, tags list/add.
Matches the Libraries & Sharing section of the Prompt Management APIs
blueprint (8/8).

ASSUMPTIONS:
- GET /prompt-library is a PUBLIC read across all published entries (any
  authenticated user can browse the library, not just their own
  publications) — this is the point of a shared "library" feature.
  POST /prompt-library (publishing) still requires the caller to own the
  source prompt.
- Publishing takes a SNAPSHOT (title/content/tags) at publish time, not a
  live reference — editing the original prompt afterward does not update
  already-published library entries.
- /prompt-share and its DELETE counterpart require the caller to own the
  prompt being shared (mirrors organizations.py-style ownership checks).
- /prompt-favorite and its DELETE counterpart do NOT require ownership —
  favoriting is treated as a personal bookmark on any prompt that exists
  (your own, one shared with you, or one you found in the library), so
  only existence is checked, not ownership. Tighten this if you want
  favorites restricted to prompts the caller actually has access to.
- GET /prompt-tags aggregates unique tags across the CALLER's OWN prompts
  only (from prompts_db), not library-wide tags.
- POST /prompt-tags adds tags to one of the caller's own prompts (merges
  into prompts_db's existing tags list, deduplicated) — this mutates
  prompts_db entries directly (same dict object imported from prompts.py,
  not a modification to that file).

No route-ordering concerns: every path here (/prompt-library, /prompt-share,
/prompt-favorite, /prompt-tags) is a flat, distinct, top-level name under
/api/v1 — none share a prefix with prompts.router's /api/v1/prompts/{id}.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.prompt_libraries import (
    PromptLibraryPublishRequest,
    PromptLibraryEntryOut,
    PromptShareRequest,
    PromptShareResponse,
    PromptFavoriteRequest,
    PromptFavoriteResponse,
    PromptTagsResponse,
    PromptTagsAddRequest,
    PromptTagsAddResponse,
)
from app.routers.prompts import prompts_db, _get_prompt_or_404, _require_owner
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1", tags=["Prompt Libraries & Sharing"])

# library_entry_id -> {..., published_by, created_at}
prompt_library_db: dict[str, dict] = {}

# prompt_id -> set of emails the prompt is shared with
prompt_shares_db: dict[str, set] = {}

# email -> set of favorited prompt_ids
prompt_favorites_db: dict[str, set] = {}


@router.get("/prompt-library", response_model=list[PromptLibraryEntryOut])
def browse_prompt_library():
    entries = list(prompt_library_db.values())
    entries.sort(key=lambda e: e["created_at"], reverse=True)
    return entries


@router.post("/prompt-library", response_model=PromptLibraryEntryOut, status_code=201)
def publish_to_prompt_library(
    data: PromptLibraryPublishRequest,
    current_user: dict = Depends(get_current_user),
):
    prompt = _get_prompt_or_404(data.prompt_id)
    _require_owner(prompt, current_user["email"])
    entry_id = str(uuid4())
    entry = {
        "id": entry_id,
        "prompt_id": data.prompt_id,
        "title": data.title or prompt["title"],
        "content": prompt["content"],
        "tags": list(prompt["tags"]),
        "published_by": current_user["email"],
        "created_at": datetime.now(timezone.utc),
    }
    prompt_library_db[entry_id] = entry
    return entry


@router.post("/prompt-share", response_model=PromptShareResponse, status_code=201)
def share_prompt(data: PromptShareRequest, current_user: dict = Depends(get_current_user)):
    prompt = _get_prompt_or_404(data.prompt_id)
    _require_owner(prompt, current_user["email"])
    shares = prompt_shares_db.setdefault(data.prompt_id, set())
    shares.add(data.email)
    return PromptShareResponse(prompt_id=data.prompt_id, shared_with=sorted(shares))


@router.delete("/prompt-share", response_model=PromptShareResponse)
def unshare_prompt(data: PromptShareRequest, current_user: dict = Depends(get_current_user)):
    prompt = _get_prompt_or_404(data.prompt_id)
    _require_owner(prompt, current_user["email"])
    shares = prompt_shares_db.setdefault(data.prompt_id, set())
    shares.discard(data.email)
    return PromptShareResponse(prompt_id=data.prompt_id, shared_with=sorted(shares))


@router.post("/prompt-favorite", response_model=PromptFavoriteResponse, status_code=201)
def favorite_prompt(data: PromptFavoriteRequest, current_user: dict = Depends(get_current_user)):
    _get_prompt_or_404(data.prompt_id)  # existence check only — see docstring
    favorites = prompt_favorites_db.setdefault(current_user["email"], set())
    favorites.add(data.prompt_id)
    return PromptFavoriteResponse(prompt_id=data.prompt_id, favorited=True)


@router.delete("/prompt-favorite", response_model=PromptFavoriteResponse)
def unfavorite_prompt(data: PromptFavoriteRequest, current_user: dict = Depends(get_current_user)):
    _get_prompt_or_404(data.prompt_id)
    favorites = prompt_favorites_db.setdefault(current_user["email"], set())
    favorites.discard(data.prompt_id)
    return PromptFavoriteResponse(prompt_id=data.prompt_id, favorited=False)


@router.get("/prompt-tags", response_model=PromptTagsResponse)
def list_prompt_tags(current_user: dict = Depends(get_current_user)):
    tags: set[str] = set()
    for p in prompts_db.values():
        if p["owner_email"] == current_user["email"]:
            tags.update(p["tags"])
    return PromptTagsResponse(tags=sorted(tags))


@router.post("/prompt-tags", response_model=PromptTagsAddResponse, status_code=201)
def add_prompt_tags(data: PromptTagsAddRequest, current_user: dict = Depends(get_current_user)):
    prompt = _get_prompt_or_404(data.prompt_id)
    _require_owner(prompt, current_user["email"])
    merged = list(dict.fromkeys(prompt["tags"] + data.tags))  # dedupe, preserve order
    prompt["tags"] = merged
    return PromptTagsAddResponse(prompt_id=data.prompt_id, tags=merged)