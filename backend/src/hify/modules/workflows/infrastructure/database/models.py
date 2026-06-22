from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from hify.modules.workflows.domain.value_objects import WorkflowStatus, default_workflow_definition
from hify.shared.domain.clock import utc_now
from hify.shared.domain.ids import new_uuid
from hify.shared.infrastructure.database import Base


class WorkflowModel(Base):
    __tablename__ = "workflows_workflows"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name="ck_workflows_workflows__status",
        ),
        CheckConstraint(
            "length(btrim(name)) > 0",
            name="ck_workflows_workflows__name_not_blank",
        ),
        CheckConstraint(
            "latest_version_number >= 0",
            name="ck_workflows_workflows__latest_version_number_non_negative",
        ),
        Index(
            "uq_workflows_workflows__team_name_lower",
            "team_id",
            text("lower(name)"),
            unique=True,
        ),
        Index(
            "ix_workflows_workflows__team_status_created_id",
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
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=WorkflowStatus.DRAFT.value,
    )
    draft_definition: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=default_workflow_definition,
        server_default=text("'{}'::jsonb"),
    )
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


class WorkflowVersionModel(Base):
    __tablename__ = "workflows_versions"
    __table_args__ = (
        CheckConstraint(
            "version_number > 0",
            name="ck_workflows_versions__version_number_positive",
        ),
        CheckConstraint(
            "length(btrim(name)) > 0",
            name="ck_workflows_versions__name_not_blank",
        ),
        Index(
            "uq_workflows_versions__workflow_version_number",
            "workflow_id",
            "version_number",
            unique=True,
        ),
        Index(
            "ix_workflows_versions__team_workflow_version",
            "team_id",
            "workflow_id",
            "version_number",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    team_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    workflow_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("workflows_workflows.id"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(BigInteger, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    definition: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    published_by: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
    )
