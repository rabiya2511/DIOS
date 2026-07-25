"""
Pydantic schemas for the Moderation & Feedback domain.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ReportRequest(BaseModel):
    message_id: str
    reason: str


class ReportOut(BaseModel):
    id: str
    message_id: str
    reporter_email: str
    reason: str
    timestamp: datetime


class FeedbackRequest(BaseModel):
    message_id: str
    rating: str  # "up" or "down"
    comment: Optional[str] = None


class FeedbackOut(BaseModel):
    id: str
    message_id: str
    user_email: str
    rating: str
    comment: Optional[str] = None
    timestamp: datetime


class ModerateRequest(BaseModel):
    message_id: str
    action: str  # e.g. "hide", "warn", "remove"


class ModerateOut(BaseModel):
    id: str
    message_id: str
    action: str
    moderator_email: str
    timestamp: datetime


class ConversationRateRequest(BaseModel):
    conversation_id: str
    rating: int  # 1-5


class ConversationRateOut(BaseModel):
    id: str
    conversation_id: str
    user_email: str
    rating: int
    timestamp: datetime


class ConversationAnalyticsOut(BaseModel):
    conversation_id: str
    total_reports: int
    total_feedback: int
    average_rating: Optional[float] = None


class ConversationMetricsOut(BaseModel):
    total_reports: int
    total_feedback: int
    total_moderation_actions: int
    total_ratings: int