from __future__ import annotations

from uuid import UUID

from hify.shared.domain.ids import new_uuid, parse_uuid


def test_new_uuid_generates_uuidv7() -> None:
    value = new_uuid()

    assert value.version == 7


def test_parse_uuid_accepts_uuid_or_string() -> None:
    value = new_uuid()

    assert parse_uuid(value) is value
    assert parse_uuid(str(value)) == value
    assert isinstance(parse_uuid(str(value)), UUID)
