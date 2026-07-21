"""
Sessions router — list, revoke one, revoke-except-current, revoke-all.
Matches the Sessions section of the User Management blueprint (the
4 session-specific endpoints — device endpoints are covered by the
existing app/routers/devices.py, so they're not duplicated here).
"""

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.sessions import SessionOut
from app.models.user import sessions_db
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/sessions", tags=["Sessions"])


@router.get("", response_model=list[SessionOut])
def list_sessions(
    current_session_id: str = None,
    current_user: dict = Depends(get_current_user),
):
    email = current_user["email"]
    result = []
    for s in sessions_db.values():
        if s["owner_email"] == email:
            result.append({**s, "current": s["id"] == current_session_id})
    return result


@router.delete("/{session_id}", status_code=204)
def revoke_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
):
    session = sessions_db.get(session_id)
    if not session or session["owner_email"] != current_user["email"]:
        raise HTTPException(status_code=404, detail="Session not found")
    del sessions_db[session_id]
    return None


@router.delete("", status_code=204)
def revoke_all_except_current(
    current_session_id: str,
    current_user: dict = Depends(get_current_user),
):
    email = current_user["email"]
    to_delete = [sid for sid, s in sessions_db.items() if s["owner_email"] == email and sid != current_session_id]
    for sid in to_delete:
        del sessions_db[sid]
    return None


@router.post("/revoke-all", status_code=204)
def revoke_all_sessions(current_user: dict = Depends(get_current_user)):
    email = current_user["email"]
    to_delete = [sid for sid, s in sessions_db.items() if s["owner_email"] == email]
    for sid in to_delete:
        del sessions_db[sid]
    return None