"""
Devices router — list, register, trust, delete, logout.
Matches the Devices section of the Auth blueprint (5/5).
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.devices import (
    DeviceRegisterRequest,
    DeviceTrustRequest,
    DeviceOut,
    DeviceLogoutRequest,
)
from app.models.user import devices_db
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/devices", tags=["Devices"])


@router.get("", response_model=list[DeviceOut])
def list_devices(current_user: dict = Depends(get_current_user)):
    email = current_user["email"]
    return [d for d in devices_db.values() if d["owner_email"] == email]


@router.post("/register", response_model=DeviceOut, status_code=201)
def register_device(
    data: DeviceRegisterRequest,
    current_user: dict = Depends(get_current_user),
):
    device_id = str(uuid4())
    now = datetime.now(timezone.utc)
    device = {
        "id": device_id,
        "owner_email": current_user["email"],
        "name": data.name,
        "trusted": False,
        "active": True,
        "created_at": now,
        "last_active_at": now,
    }
    devices_db[device_id] = device
    return device


@router.patch("/trust", response_model=DeviceOut)
def trust_device(
    data: DeviceTrustRequest,
    current_user: dict = Depends(get_current_user),
):
    device = devices_db.get(data.device_id)
    if not device or device["owner_email"] != current_user["email"]:
        raise HTTPException(status_code=404, detail="Device not found")

    device["trusted"] = data.trusted
    return device


@router.delete("/{device_id}", status_code=204)
def delete_device(
    device_id: str,
    current_user: dict = Depends(get_current_user),
):
    device = devices_db.get(device_id)
    if not device or device["owner_email"] != current_user["email"]:
        raise HTTPException(status_code=404, detail="Device not found")

    del devices_db[device_id]
    return None


@router.post("/logout", status_code=204)
def logout_device(
    data: DeviceLogoutRequest,
    current_user: dict = Depends(get_current_user),
):
    device = devices_db.get(data.device_id)
    if not device or device["owner_email"] != current_user["email"]:
        raise HTTPException(status_code=404, detail="Device not found")

    device["active"] = False
    return None