from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from hify.modules.conversations.domain.errors import ConversationValidationError


class ConversationStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class MessageStatus(StrEnum):
    CREATED = "created"
    REDACTED = "redacted"


class MessageFeedbackRating(StrEnum):
    POSITIVE = "positive"
    NEGATIVE = "negative"


def normalize_conversation_title(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.strip().split())
    if not normalized:
        return None
    if len(normalized) > 200:
        raise ConversationValidationError("conversation title must be at most 200 characters")
    return normalized


def normalize_message_content(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ConversationValidationError("message content must not be blank")
    if len(normalized) > 200000:
        raise ConversationValidationError("message content must be at most 200000 characters")
    return normalized


def normalize_idempotency_key(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ConversationValidationError("idempotency key must not be blank")
    if len(normalized) > 120:
        raise ConversationValidationError("idempotency key must be at most 120 characters")
    return normalized


def normalize_feedback_comment(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if len(normalized) > 2000:
        raise ConversationValidationError("feedback comment must be at most 2000 characters")
    return normalized


def parse_message_cursor(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        cursor = int(value)
    except ValueError as exc:
        raise ConversationValidationError("message cursor is invalid") from exc
    if cursor < 0:
        raise ConversationValidationError("message cursor is invalid")
    return cursor


def format_conversation_cursor(created_at: datetime, conversation_id: UUID) -> str:
    return f"{created_at.isoformat()}|{conversation_id}"


def parse_conversation_cursor(value: str | None) -> tuple[datetime, UUID] | None:
    if value is None:
        return None

    created_at_value, separator, conversation_id_value = value.partition("|")
    if separator != "|":
        raise ConversationValidationError("conversation cursor is invalid")

    try:
        created_at = datetime.fromisoformat(created_at_value)
        conversation_id = UUID(conversation_id_value)
    except ValueError as exc:
        raise ConversationValidationError("conversation cursor is invalid") from exc

    return created_at, conversation_id
