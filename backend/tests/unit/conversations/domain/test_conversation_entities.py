from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from hify.modules.conversations.domain.entities import Conversation, MessageFeedback
from hify.modules.conversations.domain.errors import ConversationValidationError
from hify.modules.conversations.domain.value_objects import MessageFeedbackRating, MessageRole


def test_create_conversation_normalizes_title_and_appends_message() -> None:
    now = datetime(2026, 6, 22, tzinfo=UTC)
    conversation = Conversation.create(
        team_id=UUID("00000000-0000-7000-8000-000000000001"),
        agent_id=UUID("00000000-0000-7000-8000-000000000002"),
        title="  Support   Chat ",
        created_by=UUID("00000000-0000-7000-8000-000000000003"),
        now=now,
    )

    message = conversation.append_message(
        role=MessageRole.USER,
        content="  Hello ",
        created_by=UUID("00000000-0000-7000-8000-000000000003"),
        idempotency_key="  request-1 ",
        now=now,
    )

    assert conversation.title == "Support Chat"
    assert conversation.message_count == 1
    assert conversation.version == 1
    assert message.sequence_number == 1
    assert message.content == "Hello"
    assert message.idempotency_key == "request-1"


def test_append_message_rejects_blank_content() -> None:
    now = datetime(2026, 6, 22, tzinfo=UTC)
    conversation = Conversation.create(
        team_id=UUID("00000000-0000-7000-8000-000000000001"),
        agent_id=UUID("00000000-0000-7000-8000-000000000002"),
        title=None,
        created_by=UUID("00000000-0000-7000-8000-000000000003"),
        now=now,
    )

    with pytest.raises(ConversationValidationError, match="content"):
        conversation.append_message(
            role=MessageRole.USER,
            content="   ",
            created_by=UUID("00000000-0000-7000-8000-000000000003"),
            idempotency_key="request-1",
            now=now,
        )


def test_feedback_update_normalizes_comment_and_increments_version() -> None:
    now = datetime(2026, 6, 22, tzinfo=UTC)
    feedback = MessageFeedback.create(
        team_id=UUID("00000000-0000-7000-8000-000000000001"),
        conversation_id=UUID("00000000-0000-7000-8000-000000000002"),
        message_id=UUID("00000000-0000-7000-8000-000000000003"),
        rating=MessageFeedbackRating.POSITIVE,
        comment=" good ",
        created_by=UUID("00000000-0000-7000-8000-000000000004"),
        now=now,
    )

    feedback.update(rating=MessageFeedbackRating.NEGATIVE, comment="  bad answer ", now=now)

    assert feedback.rating == MessageFeedbackRating.NEGATIVE
    assert feedback.comment == "bad answer"
    assert feedback.version == 1
