"""
Email router — send, templates (list/create), history.
Matches the Email section of the Notifications APIs blueprint (4/4).
STUBBED: send doesn't hit a real mail provider — it logs to
email_history_db and returns a simulated "sent" status.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.email import (
    EmailTemplateCreateRequest,
    EmailTemplateResponse,
    EmailSendRequest,
    EmailSendResponse,
    EmailHistoryEntry,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/email", tags=["Email"])

# id -> {id, name, subject, body, created_at}
email_templates_db: dict[str, dict] = {}

# append-only send log
email_history_db: list[dict] = []


@router.post("/send", response_model=EmailSendResponse, status_code=201)
def send_email(
    data: EmailSendRequest,
    current_user: dict = Depends(get_current_user),
):
    subject = data.subject
    body = data.body

    if data.template_id:
        template = email_templates_db.get(data.template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Email template not found")
        subject = subject or template["subject"]
        body = body or template["body"]

    if not subject or not body:
        raise HTTPException(
            status_code=422,
            detail="subject and body are required (directly or via template_id)",
        )

    email_id = str(uuid4())
    now = datetime.now(timezone.utc)
    entry = {
        "id": email_id,
        "to_email": data.to_email,
        "subject": subject,
        "body": body,
        "template_id": data.template_id,
        "status": "sent",  # STUB: always succeeds
        "sent_at": now,
    }
    email_history_db.append(entry)
    return entry


@router.get("/templates", response_model=list[EmailTemplateResponse])
def list_templates():
    return list(email_templates_db.values())


@router.post("/templates", response_model=EmailTemplateResponse, status_code=201)
def create_template(
    data: EmailTemplateCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    template_id = str(uuid4())
    now = datetime.now(timezone.utc)
    email_templates_db[template_id] = {
        "id": template_id,
        "name": data.name,
        "subject": data.subject,
        "body": data.body,
        "created_at": now,
    }
    return email_templates_db[template_id]


@router.get("/history", response_model=list[EmailHistoryEntry])
def get_history():
    return list(email_history_db)