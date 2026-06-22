from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from hify.modules.knowledge.domain.entities import KnowledgeBase, KnowledgeChunk
from hify.modules.knowledge.domain.errors import KnowledgeValidationError
from hify.modules.knowledge.domain.services import split_document_text
from hify.modules.knowledge.domain.value_objects import EMBEDDING_DIMENSIONS, KnowledgeBaseStatus


def test_create_knowledge_base_normalizes_fields() -> None:
    now = datetime(2026, 6, 22, tzinfo=UTC)

    knowledge_base = KnowledgeBase.create(
        team_id=UUID("00000000-0000-7000-8000-000000000001"),
        name=" Team Docs ",
        description=" Internal answers ",
        embedding_model_id=UUID("00000000-0000-7000-8000-000000000002"),
        embedding_dimensions=EMBEDDING_DIMENSIONS,
        created_by=UUID("00000000-0000-7000-8000-000000000003"),
        now=now,
    )

    assert knowledge_base.name == "Team Docs"
    assert knowledge_base.description == "Internal answers"
    assert knowledge_base.status is KnowledgeBaseStatus.ACTIVE
    assert knowledge_base.document_count == 0
    assert knowledge_base.chunk_count == 0


def test_create_knowledge_base_rejects_wrong_dimensions() -> None:
    now = datetime(2026, 6, 22, tzinfo=UTC)

    with pytest.raises(KnowledgeValidationError):
        KnowledgeBase.create(
            team_id=UUID("00000000-0000-7000-8000-000000000001"),
            name="Team Docs",
            description=None,
            embedding_model_id=UUID("00000000-0000-7000-8000-000000000002"),
            embedding_dimensions=768,
            created_by=UUID("00000000-0000-7000-8000-000000000003"),
            now=now,
        )


def test_split_document_text_uses_overlap() -> None:
    chunks = split_document_text("abcdefghij", max_chunk_characters=4, overlap_characters=1)

    assert chunks == ("abcd", "defg", "ghij")


def test_chunk_requires_fixed_embedding_dimensions() -> None:
    now = datetime(2026, 6, 22, tzinfo=UTC)

    with pytest.raises(KnowledgeValidationError):
        KnowledgeChunk.create(
            team_id=UUID("00000000-0000-7000-8000-000000000001"),
            knowledge_base_id=UUID("00000000-0000-7000-8000-000000000002"),
            document_id=UUID("00000000-0000-7000-8000-000000000003"),
            position=0,
            content="hello",
            embedding=(0.1, 0.2),
            token_count=1,
            now=now,
        )
