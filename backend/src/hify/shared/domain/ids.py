from __future__ import annotations

from uuid import UUID

import uuid6


def new_uuid() -> UUID:
    return uuid6.uuid7()


def parse_uuid(value: UUID | str) -> UUID:
    if isinstance(value, UUID):
        return value
    return UUID(value)
