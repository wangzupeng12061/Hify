from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from hify.modules.tools.domain.value_objects import ToolStatus
from hify.shared.domain.clock import utc_now
from hify.shared.domain.ids import new_uuid
from hify.shared.infrastructure.database import Base


class ToolDefinitionModel(Base):
    __tablename__ = "tools_definitions"
    __table_args__ = (
        CheckConstraint(
            "tool_kind IN ('builtin', 'http')",
            name="ck_tools_definitions__tool_kind",
        ),
        CheckConstraint(
            "status IN ('active', 'disabled')",
            name="ck_tools_definitions__status",
        ),
        CheckConstraint(
            "http_method IS NULL OR http_method IN ('GET', 'POST', 'PUT', 'PATCH', 'DELETE')",
            name="ck_tools_definitions__http_method",
        ),
        CheckConstraint(
            "length(btrim(name)) > 0",
            name="ck_tools_definitions__name_not_blank",
        ),
        CheckConstraint(
            "jsonb_typeof(input_schema) = 'object'",
            name="ck_tools_definitions__input_schema_object",
        ),
        Index(
            "uq_tools_definitions__team_name_lower",
            "team_id",
            text("lower(name)"),
            unique=True,
        ),
        Index(
            "ix_tools_definitions__team_status_created_id",
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
    tool_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=ToolStatus.ACTIVE.value)
    input_schema: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    builtin_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    endpoint_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    http_method: Mapped[str | None] = mapped_column(String(32), nullable=True)
    http_headers: Mapped[dict[str, str]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
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
