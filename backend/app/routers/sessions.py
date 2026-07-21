"""
Sessions domain router (FastAPI)
--------------------------------
Implements the 8 Sessions endpoints from the blueprint:

  GET    /sessions
  DELETE /sessions/{id}
  DELETE /sessions
  POST   /sessions/revoke-all
  GET    /devices
  POST   /devices/register
  DELETE /devices/{id}
  PATCH  /devices/trust

Assumptions (adjust to match your actual project):
  - You already have a `get_current_user` dependency that decodes the JWT
    and returns a user object/dict with at least an `id` field.
  - You have a DB session dependency `get_db` (SQLAlchemy-style). If you're
    using something else (Tortoise, Prisma, raw Mongo, in-memory dict),
    swap out the DB calls — the route signatures/logic stay the same.
  - Sessions are created at login time (not shown here) and tied to
    user_id + a session/device fingerprint.

Wire this into your app with:
    from sessions_router import router as sessions_router
    app.include_router(sessions_router, prefix="/api/v1", tags=["Sessions"])
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

# --- Replace these with your actual project's dependencies ---
from auth import get_current_user          # returns current authenticated user
from database import get_db                # returns a DB session
# ---------------------------------------------------------------

router = APIRouter()


# ---------- Schemas ----------

class SessionOut(BaseModel):
    id: str
    device: Optional[str] = None
    ip: Optional[str] = None
    created_at: datetime
    last_active_at: Optional[datetime] = None
    current: bool = False


class DeviceRegisterIn(BaseModel):
    device_name: str
    device_type: Optional[str] = None  # e.g. "mobile", "desktop", "browser"
    push_token: Optional[str] = None


class DeviceOut(BaseModel):
    id: str
    device_name: str
    device_type: Optional[str] = None
    trusted: bool = False
    registered_at: datetime


class DeviceTrustIn(BaseModel):
    device_id: str
    trusted: bool


# ---------- Sessions ----------

@router.get("/sessions", response_model=list[SessionOut])
def list_sessions(current_user=Depends(get_current_user), db=Depends(get_db)):
    """List all active sessions for the current user."""
    sessions = db.query_sessions(user_id=current_user.id)
    return sessions


@router.delete("/sessions/{id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_session(id: str, current_user=Depends(get_current_user), db=Depends(get_db)):
    """Revoke (log out) a single session by id."""
    session = db.get_session(id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    db.delete_session(id)
    return None


@router.delete("/sessions", status_code=status.HTTP_204_NO_CONTENT)
def revoke_all_sessions_except_current(
    current_user=Depends(get_current_user), db=Depends(get_db)
):
    """Revoke every session for the user except the one making this request."""
    db.delete_all_sessions(user_id=current_user.id, exclude_current=True)
    return None


@router.post("/sessions/revoke-all", status_code=status.HTTP_204_NO_CONTENT)
def revoke_all_sessions(current_user=Depends(get_current_user), db=Depends(get_db)):
    """Revoke ALL sessions for the user, including the current one (force logout everywhere)."""
    db.delete_all_sessions(user_id=current_user.id, exclude_current=False)
    return None


# ---------- Devices ----------

@router.get("/devices", response_model=list[DeviceOut])
def list_devices(current_user=Depends(get_current_user), db=Depends(get_db)):
    """List all devices registered to the current user."""
    devices = db.query_devices(user_id=current_user.id)
    return devices


@router.post("/devices/register", response_model=DeviceOut, status_code=status.HTTP_201_CREATED)
def register_device(
    payload: DeviceRegisterIn,
    current_user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Register a new device for the current user."""
    device = {
        "id": str(uuid4()),
        "user_id": current_user.id,
        "device_name": payload.device_name,
        "device_type": payload.device_type,
        "push_token": payload.push_token,
        "trusted": False,
        "registered_at": datetime.now(timezone.utc),
    }
    db.create_device(device)
    return device


@router.delete("/devices/{id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_device(id: str, current_user=Depends(get_current_user), db=Depends(get_db)):
    """Unregister/remove a device."""
    device = db.get_device(id)
    if not device or device.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Device not found")
    db.delete_device(id)
    return None


@router.patch("/devices/trust", response_model=DeviceOut)
def set_device_trust(
    payload: DeviceTrustIn,
    current_user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Mark a device as trusted or untrusted."""
    device = db.get_device(payload.device_id)
    if not device or device.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Device not found")
    updated = db.update_device(payload.device_id, trusted=payload.trusted)
    return updated