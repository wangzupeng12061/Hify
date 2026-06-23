from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Index, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from hify.shared.domain.clock import utc_now
from hify.shared.domain.ids import new_uuid
from hify.shared.infrastructure.database import Base


class UsageRecordModel(Base):
    __tablename__ = "usage_records"
    __table_args__ = (
        CheckConstraint(
            "length(btrim(provider)) > 0",
            name="ck_usage_records__provider_not_blank",
        ),
        CheckConstraint(
            "length(btrim(model)) > 0",
            name="ck_usage_records__model_not_blank",
        ),
        CheckConstraint(
            "length(btrim(idempotency_key)) > 0",
            name="ck_usage_records__idempotency_key_not_blank",
        ),
        CheckConstraint("input_tokens >= 0", name="ck_usage_records__input_tokens"),
        CheckConstraint("output_tokens >= 0", name="ck_usage_records__output_tokens"),
        CheckConstraint("total_tokens >= 0", name="ck_usage_records__total_tokens"),
        CheckConstraint("cost_amount >= 0", name="ck_usage_records__cost_amount"),
        Index(
            "uq_usage_records__team_idempotency_key",
            "team_id",
            "idempotency_key",
            unique=True,
        ),
        Index(
            "ix_usage_records__team_occurred_id",
            "team_id",
            "occurred_at",
            "id",
        ),
        Index(
            "ix_usage_records__team_run_occurred_id",
            "team_id",
            "run_id",
            "occurred_at",
            "id",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    team_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    run_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    agent_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    agent_version_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    provider_model_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(Text, nullable=False)
    input_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False)
    output_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False)
    total_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False)
    cost_amount: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(Text, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class UsageQuotaModel(Base):
    __tablename__ = "usage_quotas"
    __table_args__ = (
        CheckConstraint(
            "monthly_token_limit IS NULL OR monthly_token_limit > 0",
            name="ck_usage_quotas__monthly_token_limit",
        ),
        Index("uq_usage_quotas__team", "team_id", unique=True),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    team_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    monthly_token_limit: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    version: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    created_by: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    updated_by: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
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
