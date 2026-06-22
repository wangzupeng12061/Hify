from __future__ import annotations

from hify.modules.knowledge.domain.value_objects import (
    CHUNK_OVERLAP_CHARACTERS,
    MAX_CHUNK_CHARACTERS,
    normalize_document_content,
)


def split_document_text(
    content: str,
    *,
    max_chunk_characters: int = MAX_CHUNK_CHARACTERS,
    overlap_characters: int = CHUNK_OVERLAP_CHARACTERS,
) -> tuple[str, ...]:
    normalized = normalize_document_content(content)
    if max_chunk_characters < 1:
        raise ValueError("max_chunk_characters must be positive")
    if overlap_characters < 0 or overlap_characters >= max_chunk_characters:
        raise ValueError("overlap_characters must be smaller than max_chunk_characters")

    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(start + max_chunk_characters, len(normalized))
        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(normalized):
            break
        start = end - overlap_characters
    return tuple(chunks)
