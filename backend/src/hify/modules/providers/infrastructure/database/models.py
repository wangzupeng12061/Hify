from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Index, Numeric
from sqlalchemy import LargeBinary, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from hify.modules.providers.domain.value_objects import (
    CredentialStatus,
    ModelKind,
    ModelStatus,
    ProviderStatus,
)
from hify.shared.domain.clock import utc_now
from hify.shared.domain.ids import new_uuid
from hify.shared.infrastructure.database import Base


class ModelProviderModel(Base):
    __tablename__ = "providers_providers"
    __table_args__ = (
        CheckConstraint(
            "provider_type IN ('openai', 'anthropic', 'gemini', 'ollama', 'deepseek')",
            name="ck_providers_providers__provider_type",
        ),
        CheckConstraint(
            "status IN ('active', 'disabled')",
            name="ck_providers_providers__status",
        ),
        CheckConstraint(
            "length(btrim(name)) > 0",
            name="ck_providers_providers__name_not_blank",
        ),
        Index(
            "uq_providers_providers__team_type_name_lower",
            "team_id",
            "provider_type",
            text("lower(name)"),
            unique=True,
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    team_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    provider_type: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    base_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=ProviderStatus.ACTIVE.value)
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


class ProviderCredentialModel(Base):
    __tablename__ = "providers_credentials"
    __table_args__ = (
        UniqueConstraint("provider_id", name="uq_providers_credentials__provider_id"),
        CheckConstraint(
            "status IN ('active', 'disabled')",
            name="ck_providers_credentials__status",
        ),
        CheckConstraint(
            "key_version > 0",
            name="ck_providers_credentials__key_version_positive",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    team_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    provider_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("providers_providers.id"),
        nullable=False,
    )
    secret_ciphertext: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    key_version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    secret_fingerprint: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=CredentialStatus.ACTIVE.value)
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


class ProviderModelModel(Base):
    __tablename__ = "providers_models"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('chat', 'embedding')",
            name="ck_providers_models__kind",
        ),
        CheckConstraint(
            "status IN ('active', 'disabled')",
            name="ck_providers_models__status",
        ),
        CheckConstraint(
            "length(btrim(model_name)) > 0",
            name="ck_providers_models__model_name_not_blank",
        ),
        CheckConstraint(
            "length(btrim(display_name)) > 0",
            name="ck_providers_models__display_name_not_blank",
        ),
        CheckConstraint(
            "context_window_tokens > 0",
            name="ck_providers_models__context_window_tokens_positive",
        ),
        CheckConstraint(
            "price_per_1m_input_tokens IS NULL OR price_per_1m_input_tokens >= 0",
            name="ck_providers_models__input_price_non_negative",
        ),
        CheckConstraint(
            "price_per_1m_output_tokens IS NULL OR price_per_1m_output_tokens >= 0",
            name="ck_providers_models__output_price_non_negative",
        ),
        Index(
            "uq_providers_models__provider_model_name_lower",
            "provider_id",
            text("lower(model_name)"),
            unique=True,
        ),
        Index(
            "ix_providers_models__team_status_created_id",
            "team_id",
            "status",
            "created_at",
            "id",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    team_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    provider_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("providers_providers.id"),
        nullable=False,
    )
    model_name: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False, default=ModelKind.CHAT.value)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=ModelStatus.ACTIVE.value)
    context_window_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False)
    supports_tools: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    supports_vision: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    supports_structured_output: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    price_per_1m_input_tokens: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 8),
        nullable=True,
    )
    price_per_1m_output_tokens: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 8),
        nullable=True,
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
