from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from hify.modules.conversations.domain.value_objects import (
    ConversationStatus,
    MessageFeedbackRating,
    MessageRole,
    MessageStatus,
)
from hify.shared.domain.clock import utc_now
from hify.shared.domain.ids import new_uuid
from hify.shared.infrastructure.database import Base


class ConversationModel(Base):
    __tablename__ = "conversations_conversations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'archived')",
            name="ck_conversations_conversations__status",
        ),
        CheckConstraint(
            "title IS NULL OR length(btrim(title)) > 0",
            name="ck_conversations_conversations__title_not_blank",
        ),
        CheckConstraint(
            "message_count >= 0",
            name="ck_conversations_conversations__message_count_non_negative",
        ),
        Index(
            "ix_conversations_conversations__team_status_created_id",
            "team_id",
            "status",
            "created_at",
            "id",
        ),
        Index(
            "ix_conversations_conversations__team_agent_created_id",
            "team_id",
            "agent_id",
            "created_at",
            "id",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    team_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    agent_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ConversationStatus.ACTIVE.value,
    )
    message_count: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    version: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    created_by: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class ConversationMessageModel(Base):
    __tablename__ = "conversations_messages"
    __table_args__ = (
        CheckConstraint(
            "sequence_number > 0",
            name="ck_conversations_messages__sequence_number_positive",
        ),
        CheckConstraint(
            "role IN ('user', 'assistant', 'system', 'tool')",
            name="ck_conversations_messages__role",
        ),
        CheckConstraint(
            "status IN ('created', 'redacted')",
            name="ck_conversations_messages__status",
        ),
        CheckConstraint(
            "length(btrim(content)) > 0",
            name="ck_conversations_messages__content_not_blank",
        ),
        CheckConstraint(
            "length(btrim(idempotency_key)) > 0",
            name="ck_conversations_messages__idempotency_key_not_blank",
        ),
        Index(
            "uq_conversations_messages__conversation_sequence",
            "conversation_id",
            "sequence_number",
            unique=True,
        ),
        Index(
            "uq_conversations_messages__team_conversation_idempotency",
            "team_id",
            "conversation_id",
            "idempotency_key",
            unique=True,
        ),
        Index(
            "ix_conversations_messages__team_conversation_sequence",
            "team_id",
            "conversation_id",
            "sequence_number",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    team_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    conversation_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("conversations_conversations.id"),
        nullable=False,
    )
    sequence_number: Mapped[int] = mapped_column(BigInteger, nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default=MessageRole.USER.value)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=MessageStatus.CREATED.value,
    )
    idempotency_key: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class MessageFeedbackModel(Base):
    __tablename__ = "conversations_message_feedback"
    __table_args__ = (
        CheckConstraint(
            "rating IN ('positive', 'negative')",
            name="ck_conversations_message_feedback__rating",
        ),
        Index(
            "uq_conversations_message_feedback__message_created_by",
            "message_id",
            "created_by",
            unique=True,
        ),
        Index(
            "ix_conversations_message_feedback__team_conversation_created",
            "team_id",
            "conversation_id",
            "created_at",
            "id",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    team_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    conversation_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("conversations_conversations.id"),
        nullable=False,
    )
    message_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("conversations_messages.id"),
        nullable=False,
    )
    rating: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=MessageFeedbackRating.POSITIVE.value,
    )
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    created_by: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
    )
