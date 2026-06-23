from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ConversationInfo:
    id: UUID
    team_id: UUID
    agent_id: UUID
    title: str | None
    status: str
    message_count: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class ConversationMessageInfo:
    id: UUID
    team_id: UUID
    conversation_id: UUID
    sequence_number: int
    role: str
    content: str
    status: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ConversationMessagePage:
    items: tuple[ConversationMessageInfo, ...]
    next_cursor: str | None
    has_more: bool


@dataclass(frozen=True, slots=True)
class ConversationPage:
    items: tuple[ConversationInfo, ...]
    next_cursor: str | None
    has_more: bool


@dataclass(frozen=True, slots=True)
class MessageFeedbackInfo:
    id: UUID
    team_id: UUID
    conversation_id: UUID
    message_id: UUID
    rating: str
    comment: str | None
    created_at: datetime
    updated_at: datetime
