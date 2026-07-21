"""
SMS & Push router — sms/send, push/send, push/devices, push/register-device.
Matches the SMS & Push section of the Notifications APIs blueprint (4/4).
STUBBED: send endpoints don't hit real providers — they log to history
and return a simulated "sent" status.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends

from app.schemas.sms_push import (
    SmsSendRequest,
    SmsSendResponse,
    PushDeviceRegisterRequest,
    PushDeviceResponse,
    PushSendRequest,
    PushSendResponse,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1", tags=["SMS & Push"])

# append-only send log
sms_history_db: list[dict] = []

# id -> {id, owner_email, device_token, platform, registered_at}
push_devices_db: dict[str, dict] = {}

# append-only send log
push_history_db: list[dict] = []


@router.post("/sms/send", response_model=SmsSendResponse, status_code=201)
def send_sms(
    data: SmsSendRequest,
    current_user: dict = Depends(get_current_user),
):
    sms_id = str(uuid4())
    now = datetime.now(timezone.utc)
    entry = {
        "id": sms_id,
        "to_phone": data.to_phone,
        "message": data.message,
        "status": "sent",  # STUB: always succeeds
        "sent_at": now,
    }
    sms_history_db.append(entry)
    return entry


@router.post("/push/register-device", response_model=PushDeviceResponse, status_code=201)
def register_device(
    data: PushDeviceRegisterRequest,
    current_user: dict = Depends(get_current_user),
):
    device_id = str(uuid4())
    now = datetime.now(timezone.utc)
    push_devices_db[device_id] = {
        "id": device_id,
        "owner_email": current_user["email"],
        "device_token": data.device_token,
        "platform": data.platform,
        "registered_at": now,
    }
    return push_devices_db[device_id]


@router.get("/push/devices", response_model=list[PushDeviceResponse])
def list_devices(current_user: dict = Depends(get_current_user)):
    return [
        d for d in push_devices_db.values() if d["owner_email"] == current_user["email"]
    ]


@router.post("/push/send", response_model=PushSendResponse, status_code=201)
def send_push(
    data: PushSendRequest,
    current_user: dict = Depends(get_current_user),
):
    target_devices = [d for d in push_devices_db.values() if d["owner_email"] == data.to_email]
    push_id = str(uuid4())
    now = datetime.now(timezone.utc)
    entry = {
        "id": push_id,
        "to_email": data.to_email,
        "title": data.title,
        "body": data.body,
        "devices_targeted": len(target_devices),
        "status": "sent",  # STUB: always succeeds, even with 0 devices
        "sent_at": now,
    }
    push_history_db.append(entry)
    return entry