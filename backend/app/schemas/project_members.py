"""
Pydantic schemas for the Project Members domain
(Projects & Workspace APIs blueprint).
"""

from typing import List, Literal

from pydantic import BaseModel, EmailStr

ProjectRole = Literal["owner", "admin", "member"]


class ProjectMemberOut(BaseModel):
    email: EmailStr
    role: ProjectRole


class ProjectMembersResponse(BaseModel):
    project_id: str
    members: List[ProjectMemberOut]


class ProjectMemberAddRequest(BaseModel):
    email: EmailStr
    role: ProjectRole = "member"


class ProjectMemberRoleUpdateRequest(BaseModel):
    role: ProjectRole


class ProjectMemberInviteRequest(BaseModel):
    email: EmailStr
    role: ProjectRole = "member"


class ProjectMemberBulkAddRequest(BaseModel):
    members: List[ProjectMemberAddRequest]


class ProjectMemberBulkAddResponse(BaseModel):
    added_count: int
    members: List[ProjectMemberOut]