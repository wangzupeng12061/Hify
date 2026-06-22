"""create knowledge rag tables

Revision ID: knowledge_20260622_0001
Revises: tools_20260622_0001
Create Date: 2026-06-22 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from pgvector.sqlalchemy import Vector
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "knowledge_20260622_0001"
down_revision: str | None = "tools_20260622_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


EMBEDDING_DIMENSIONS = 1536


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "knowledge_bases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("embedding_model_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("embedding_dimensions", sa.BigInteger(), nullable=False),
        sa.Column("document_count", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("chunk_count", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "status IN ('active', 'archived')",
            name="ck_knowledge_bases__status",
        ),
        sa.CheckConstraint(
            "length(btrim(name)) > 0",
            name="ck_knowledge_bases__name_not_blank",
        ),
        sa.CheckConstraint(
            f"embedding_dimensions = {EMBEDDING_DIMENSIONS}",
            name="ck_knowledge_bases__embedding_dimensions",
        ),
        sa.CheckConstraint("document_count >= 0", name="ck_knowledge_bases__document_count"),
        sa.CheckConstraint("chunk_count >= 0", name="ck_knowledge_bases__chunk_count"),
    )
    op.create_index(
        "uq_knowledge_bases__team_name_lower",
        "knowledge_bases",
        ["team_id", sa.text("lower(name)")],
        unique=True,
    )
    op.create_index(
        "ix_knowledge_bases__team_status_created_id",
        "knowledge_bases",
        ["team_id", "status", "created_at", "id"],
        unique=False,
    )

    op.create_table(
        "knowledge_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("knowledge_base_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("source_uri", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("chunk_count", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["knowledge_base_id"], ["knowledge_bases.id"]),
        sa.CheckConstraint(
            "status IN ('completed', 'failed')",
            name="ck_knowledge_documents__status",
        ),
        sa.CheckConstraint(
            "length(btrim(title)) > 0",
            name="ck_knowledge_documents__title_not_blank",
        ),
        sa.CheckConstraint("chunk_count >= 0", name="ck_knowledge_documents__chunk_count"),
        sa.CheckConstraint(
            "length(content_hash) = 64",
            name="ck_knowledge_documents__content_hash_sha256",
        ),
    )
    op.create_index(
        "ix_knowledge_documents__team_kb_created_id",
        "knowledge_documents",
        ["team_id", "knowledge_base_id", "created_at", "id"],
        unique=False,
    )

    op.create_table(
        "knowledge_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("knowledge_base_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("position", sa.BigInteger(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIMENSIONS), nullable=False),
        sa.Column("token_count", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["knowledge_base_id"], ["knowledge_bases.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["knowledge_documents.id"]),
        sa.CheckConstraint("position >= 0", name="ck_knowledge_chunks__position"),
        sa.CheckConstraint("token_count > 0", name="ck_knowledge_chunks__token_count"),
        sa.CheckConstraint(
            "length(btrim(content)) > 0",
            name="ck_knowledge_chunks__content_not_blank",
        ),
    )
    op.create_index(
        "uq_knowledge_chunks__document_position",
        "knowledge_chunks",
        ["document_id", "position"],
        unique=True,
    )
    op.create_index(
        "ix_knowledge_chunks__team_kb_document",
        "knowledge_chunks",
        ["team_id", "knowledge_base_id", "document_id"],
        unique=False,
    )
    op.execute(
        "CREATE INDEX hnsw_knowledge_chunks__embedding_cosine "
        "ON knowledge_chunks USING hnsw (embedding vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 64)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS hnsw_knowledge_chunks__embedding_cosine")
    op.drop_index("ix_knowledge_chunks__team_kb_document", table_name="knowledge_chunks")
    op.drop_index("uq_knowledge_chunks__document_position", table_name="knowledge_chunks")
    op.drop_table("knowledge_chunks")
    op.drop_index("ix_knowledge_documents__team_kb_created_id", table_name="knowledge_documents")
    op.drop_table("knowledge_documents")
    op.drop_index("ix_knowledge_bases__team_status_created_id", table_name="knowledge_bases")
    op.drop_index("uq_knowledge_bases__team_name_lower", table_name="knowledge_bases")
    op.drop_table("knowledge_bases")
