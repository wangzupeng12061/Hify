from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from hify.modules.agents.domain.value_objects import AgentStatus
from hify.shared.domain.clock import utc_now
from hify.shared.domain.ids import new_uuid
from hify.shared.infrastructure.database import Base


class AgentModel(Base):
    __tablename__ = "agents_agents"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name="ck_agents_agents__status",
        ),
        CheckConstraint(
            "length(btrim(name)) > 0",
            name="ck_agents_agents__name_not_blank",
        ),
        CheckConstraint(
            "length(btrim(system_prompt)) > 0",
            name="ck_agents_agents__system_prompt_not_blank",
        ),
        CheckConstraint(
            "latest_version_number >= 0",
            name="ck_agents_agents__latest_version_number_non_negative",
        ),
        Index(
            "uq_agents_agents__team_name_lower",
            "team_id",
            text("lower(name)"),
            unique=True,
        ),
        Index(
            "ix_agents_agents__team_status_created_id",
            "team_id",
            "status",
            "created_at",
            "id",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    team_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    provider_model_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    knowledge_base_ids: Mapped[list[UUID]] = mapped_column(
        ARRAY(PGUUID(as_uuid=True)),
        nullable=False,
        default=list,
        server_default=text("'{}'::uuid[]"),
    )
    workflow_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=AgentStatus.DRAFT.value)
    latest_version_number: Mapped[int] = mapped_column(
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


class AgentVersionModel(Base):
    __tablename__ = "agents_versions"
    __table_args__ = (
        CheckConstraint(
            "version_number > 0",
            name="ck_agents_versions__version_number_positive",
        ),
        CheckConstraint(
            "length(btrim(name)) > 0",
            name="ck_agents_versions__name_not_blank",
        ),
        CheckConstraint(
            "length(btrim(system_prompt)) > 0",
            name="ck_agents_versions__system_prompt_not_blank",
        ),
        CheckConstraint(
            "context_window_tokens > 0",
            name="ck_agents_versions__context_window_tokens_positive",
        ),
        Index(
            "uq_agents_versions__agent_version_number",
            "agent_id",
            "version_number",
            unique=True,
        ),
        Index(
            "ix_agents_versions__team_agent_version",
            "team_id",
            "agent_id",
            "version_number",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    team_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    agent_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("agents_agents.id"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(BigInteger, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    knowledge_base_ids: Mapped[list[UUID]] = mapped_column(
        ARRAY(PGUUID(as_uuid=True)),
        nullable=False,
        default=list,
        server_default=text("'{}'::uuid[]"),
    )
    workflow_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    workflow_version_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
    )
    workflow_version_number: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    workflow_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    workflow_definition: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    provider_model_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    provider_type: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_name: Mapped[str] = mapped_column(Text, nullable=False)
    model_name: Mapped[str] = mapped_column(Text, nullable=False)
    model_display_name: Mapped[str] = mapped_column(Text, nullable=False)
    context_window_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False)
    supports_tools: Mapped[bool] = mapped_column(nullable=False, default=False)
    supports_vision: Mapped[bool] = mapped_column(nullable=False, default=False)
    supports_structured_output: Mapped[bool] = mapped_column(nullable=False, default=False)
    published_by: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
    )
