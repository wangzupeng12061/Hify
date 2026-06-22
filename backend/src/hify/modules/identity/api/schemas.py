from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreateUserRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    display_name: str = Field(min_length=1, max_length=120)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    display_name: str
    status: str
    created_at: datetime
    updated_at: datetime


class CreateTeamRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    owner_user_id: UUID


class TeamResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    status: str
    created_at: datetime
    updated_at: datetime


class AddTeamMemberRequest(BaseModel):
    user_id: UUID
    role: str = Field(pattern="^(owner|admin|member|viewer)$")


class MembershipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    team_id: UUID
    user_id: UUID
    role: str
    status: str
    created_at: datetime
    updated_at: datetime


class ActorContextResponse(BaseModel):
    user_id: UUID
    team_id: UUID
    membership_id: UUID
    role: str
    permissions: tuple[str, ...]
