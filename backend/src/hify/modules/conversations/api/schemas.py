from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreateConversationRequest(BaseModel):
    agent_id: UUID
    title: str | None = Field(default=None, max_length=200)


class AppendConversationMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=200000)
    idempotency_key: str = Field(min_length=1, max_length=120)


class SubmitMessageFeedbackRequest(BaseModel):
    rating: str
    comment: str | None = Field(default=None, max_length=2000)


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    team_id: UUID
    agent_id: UUID
    title: str | None
    status: str
    message_count: int
    created_at: datetime
    updated_at: datetime


class ConversationMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    team_id: UUID
    conversation_id: UUID
    sequence_number: int
    role: str
    content: str
    status: str
    created_at: datetime


class ConversationMessagePageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: tuple[ConversationMessageResponse, ...]
    next_cursor: str | None
    has_more: bool


class MessageFeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    team_id: UUID
    conversation_id: UUID
    message_id: UUID
    rating: str
    comment: str | None
    created_at: datetime
    updated_at: datetime
