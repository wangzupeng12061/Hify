from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from hify.modules.mcp.domain.value_objects import McpServerStatus, McpToolStatus, McpTransport
from hify.shared.domain.clock import utc_now
from hify.shared.domain.ids import new_uuid
from hify.shared.infrastructure.database import Base


class McpServerModel(Base):
    __tablename__ = "mcp_servers"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'disabled')",
            name="ck_mcp_servers__status",
        ),
        CheckConstraint(
            "transport IN ('streamable_http')",
            name="ck_mcp_servers__transport",
        ),
        CheckConstraint(
            "length(btrim(name)) > 0",
            name="ck_mcp_servers__name_not_blank",
        ),
        CheckConstraint(
            "endpoint_url LIKE 'https://%'",
            name="ck_mcp_servers__endpoint_https",
        ),
        Index(
            "uq_mcp_servers__team_name_lower",
            "team_id",
            text("lower(name)"),
            unique=True,
        ),
        Index(
            "ix_mcp_servers__team_status_created_id",
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
    transport: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=McpTransport.STREAMABLE_HTTP.value,
    )
    endpoint_url: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=McpServerStatus.ACTIVE.value,
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
    last_discovered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class McpDiscoveredToolModel(Base):
    __tablename__ = "mcp_discovered_tools"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'disabled')",
            name="ck_mcp_discovered_tools__status",
        ),
        CheckConstraint(
            "length(btrim(name)) > 0",
            name="ck_mcp_discovered_tools__name_not_blank",
        ),
        CheckConstraint(
            "jsonb_typeof(input_schema) = 'object'",
            name="ck_mcp_discovered_tools__input_schema_object",
        ),
        Index(
            "uq_mcp_discovered_tools__server_name",
            "server_id",
            "name",
            unique=True,
        ),
        Index(
            "ix_mcp_discovered_tools__team_server_status_name",
            "team_id",
            "server_id",
            "status",
            "name",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    team_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    server_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("mcp_servers.id"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_schema: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=McpToolStatus.ACTIVE.value,
    )
    version: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
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
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
    )
