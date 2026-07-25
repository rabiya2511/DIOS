"""
Moderation & Feedback router — report, feedback, moderate, logs, rate,
analytics, audit, metrics.
Matches the Moderation & Feedback section of the Conversations & Chat
APIs blueprint (8/8).
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends

from app.schemas.moderation import (
    ReportRequest,
    ReportOut,
    FeedbackRequest,
    FeedbackOut,
    ModerateRequest,
    ModerateOut,
    ConversationRateRequest,
    ConversationRateOut,
    ConversationAnalyticsOut,
    ConversationMetricsOut,
)
from app.models.user import (
    message_reports_db,
    message_feedback_db,
    moderation_actions_db,
    conversation_ratings_db,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1", tags=["Moderation & Feedback"])


@router.post("/messages/report", response_model=ReportOut, status_code=201)
def report_message(
    data: ReportRequest,
    current_user: dict = Depends(get_current_user),
):
    report = {
        "id": str(uuid4()),
        "message_id": data.message_id,
        "reporter_email": current_user["email"],
        "reason": data.reason,
        "timestamp": datetime.now(timezone.utc),
    }
    message_reports_db.append(report)
    return report


@router.post("/messages/feedback", response_model=FeedbackOut, status_code=201)
def give_feedback(
    data: FeedbackRequest,
    current_user: dict = Depends(get_current_user),
):
    feedback = {
        "id": str(uuid4()),
        "message_id": data.message_id,
        "user_email": current_user["email"],
        "rating": data.rating,
        "comment": data.comment,
        "timestamp": datetime.now(timezone.utc),
    }
    message_feedback_db.append(feedback)
    return feedback


@router.post("/messages/moderate", response_model=ModerateOut, status_code=201)
def moderate_message(
    data: ModerateRequest,
    current_user: dict = Depends(get_current_user),
):
    action = {
        "id": str(uuid4()),
        "message_id": data.message_id,
        "action": data.action,
        "moderator_email": current_user["email"],
        "timestamp": datetime.now(timezone.utc),
    }
    moderation_actions_db.append(action)
    return action


@router.get("/moderation/logs", response_model=list[ModerateOut])
def get_moderation_logs(current_user: dict = Depends(get_current_user)):
    return sorted(moderation_actions_db, key=lambda x: x["timestamp"], reverse=True)


@router.post("/conversation/rate", response_model=ConversationRateOut, status_code=201)
def rate_conversation(
    data: ConversationRateRequest,
    current_user: dict = Depends(get_current_user),
):
    rating = {
        "id": str(uuid4()),
        "conversation_id": data.conversation_id,
        "user_email": current_user["email"],
        "rating": data.rating,
        "timestamp": datetime.now(timezone.utc),
    }
    conversation_ratings_db.append(rating)
    return rating


@router.get("/conversation/analytics", response_model=ConversationAnalyticsOut)
def get_conversation_analytics(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
):
    ratings = [r["rating"] for r in conversation_ratings_db if r["conversation_id"] == conversation_id]
    reports = [r for r in message_reports_db]  # NOTE: reports are per-message, not per-conversation yet
    feedback = [f for f in message_feedback_db]
    avg = round(sum(ratings) / len(ratings), 2) if ratings else None
    return ConversationAnalyticsOut(
        conversation_id=conversation_id,
        total_reports=len(reports),
        total_feedback=len(feedback),
        average_rating=avg,
    )


@router.get("/conversation/audit", response_model=list[ModerateOut])
def get_conversation_audit(current_user: dict = Depends(get_current_user)):
    return sorted(moderation_actions_db, key=lambda x: x["timestamp"], reverse=True)


@router.get("/conversation/metrics", response_model=ConversationMetricsOut)
def get_conversation_metrics(current_user: dict = Depends(get_current_user)):
    return ConversationMetricsOut(
        total_reports=len(message_reports_db),
        total_feedback=len(message_feedback_db),
        total_moderation_actions=len(moderation_actions_db),
        total_ratings=len(conversation_ratings_db),
    )