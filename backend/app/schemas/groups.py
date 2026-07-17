"""
Pydantic schemas for the Groups domain.
"""
 
from datetime import datetime
from pydantic import BaseModel

class GroupCreateRequest(BaseModel):
    name: str
    description: str | None = None

class GroupUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None

class GroupResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    created_at: datetime


class GroupMemberRequest(BaseModel):
    group_id: str
    user_email: str


class GroupMembersResponse(BaseModel):
    group_id: str
    members: list[str]  # list of user emails

class GroupSearchRequest(BaseModel):
   query: str
 