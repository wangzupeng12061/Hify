from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy import UniqueConstraint
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from hify.modules.identity.domain.value_objects import MembershipStatus, TeamRole, TeamStatus, UserStatus
from hify.shared.domain.clock import utc_now
from hify.shared.domain.ids import new_uuid
from hify.shared.infrastructure.database import Base


class UserModel(Base):
    __tablename__ = "identity_users"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'disabled')",
            name="ck_identity_users__status",
        ),
        CheckConstraint(
            "length(btrim(email)) > 0",
            name="ck_identity_users__email_not_blank",
        ),
        CheckConstraint(
            "length(btrim(display_name)) > 0",
            name="ck_identity_users__display_name_not_blank",
        ),
        Index("uq_identity_users__email_lower", text("lower(email)"), unique=True),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    email: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=UserStatus.ACTIVE.value)
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


class TeamModel(Base):
    __tablename__ = "identity_teams"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'archived')",
            name="ck_identity_teams__status",
        ),
        CheckConstraint(
            "length(btrim(name)) > 0",
            name="ck_identity_teams__name_not_blank",
        ),
        Index("uq_identity_teams__name_lower", text("lower(name)"), unique=True),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=TeamStatus.ACTIVE.value)
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


class TeamMembershipModel(Base):
    __tablename__ = "identity_memberships"
    __table_args__ = (
        UniqueConstraint("team_id", "user_id", name="uq_identity_memberships__team_user"),
        CheckConstraint(
            "role IN ('owner', 'admin', 'member', 'viewer')",
            name="ck_identity_memberships__role",
        ),
        CheckConstraint(
            "status IN ('active', 'disabled')",
            name="ck_identity_memberships__status",
        ),
        Index(
            "ix_identity_memberships__team_status_created_id",
            "team_id",
            "status",
            "created_at",
            "id",
        ),
        Index(
            "ix_identity_memberships__user_status_created_id",
            "user_id",
            "status",
            "created_at",
            "id",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    team_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("identity_teams.id"),
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("identity_users.id"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False, default=TeamRole.MEMBER.value)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=MembershipStatus.ACTIVE.value)
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


class AuthSessionModel(Base):
    __tablename__ = "identity_sessions"
    __table_args__ = (
        CheckConstraint(
            "length(btrim(session_token_hash)) > 0",
            name="ck_identity_sessions__token_hash_not_blank",
        ),
        CheckConstraint(
            "expires_at > created_at",
            name="ck_identity_sessions__expires_after_created",
        ),
        Index(
            "uq_identity_sessions__token_hash",
            "session_token_hash",
            unique=True,
        ),
        Index(
            "ix_identity_sessions__expires_at_id",
            "expires_at",
            "id",
        ),
        Index(
            "ix_identity_sessions__user_expires_id",
            "user_id",
            "expires_at",
            "id",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("identity_users.id"),
        nullable=False,
    )
    team_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("identity_teams.id"),
        nullable=False,
    )
    session_token_hash: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
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


class ExternalAccountModel(Base):
    __tablename__ = "identity_external_accounts"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "subject",
            name="uq_identity_external_accounts__provider_subject",
        ),
        CheckConstraint(
            "length(btrim(provider)) > 0",
            name="ck_identity_external_accounts__provider_not_blank",
        ),
        CheckConstraint(
            "length(btrim(subject)) > 0",
            name="ck_identity_external_accounts__subject_not_blank",
        ),
        CheckConstraint(
            "length(btrim(email)) > 0",
            name="ck_identity_external_accounts__email_not_blank",
        ),
        CheckConstraint(
            "length(btrim(display_name)) > 0",
            name="ck_identity_external_accounts__display_name_not_blank",
        ),
        Index(
            "ix_identity_external_accounts__user_provider_id",
            "user_id",
            "provider",
            "id",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("identity_users.id"),
        nullable=False,
    )
    email: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
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
