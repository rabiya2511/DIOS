"""
Schemas for the Sharing & Collaboration domain (Conversations & Chat
APIs blueprint). Operates over conversations_db from conversations.py —
no duplicate storage of conversations themselves.
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr


class ConversationShareRequest(BaseModel):
    conversation_id: str
    email: EmailStr


class ConversationShareResponse(BaseModel):
    conversation_id: str
    shared_with_email: EmailStr
    shared_at: datetime


class CommentCreateRequest(BaseModel):
    conversation_id: str
    content: str


class CommentResponse(BaseModel):
    id: str
    conversation_id: str
    author_email: EmailStr
    content: str
    created_at: datetime


class ConversationTagRequest(BaseModel):
    conversation_id: str
    tag: str


class ConversationFavoriteRequest(BaseModel):
    conversation_id: str