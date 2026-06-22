from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from datetime import tzinfo

import pytest

from hify.shared.domain.clock import ensure_utc, utc_now


def test_utc_now_returns_timezone_aware_utc_datetime() -> None:
    value = utc_now()

    assert value.tzinfo is UTC


def test_ensure_utc_converts_aware_datetime() -> None:
    value = datetime(2026, 6, 22, 8, 0, tzinfo=timezone(timedelta(hours=8)))

    assert ensure_utc(value) == datetime(2026, 6, 22, 0, 0, tzinfo=UTC)


def test_ensure_utc_rejects_naive_datetime() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        ensure_utc(datetime(2026, 6, 22, 0, 0))


def test_ensure_utc_rejects_tzinfo_without_offset() -> None:
    class BrokenTimezone(tzinfo):
        def utcoffset(self, dt: datetime | None) -> None:
            return None

    with pytest.raises(ValueError, match="timezone-aware"):
        ensure_utc(datetime(2026, 6, 22, 0, 0, tzinfo=BrokenTimezone()))
