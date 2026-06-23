from __future__ import annotations

from datetime import UTC, datetime

from hify.modules.usage.application.quota_period import month_period_for
from hify.modules.usage.domain.errors import UsageValidationError
from hify.shared.domain.clock import Clock


def resolve_usage_cost_period(
    *,
    period_start: datetime | None,
    period_end: datetime | None,
    clock: Clock,
) -> tuple[datetime, datetime]:
    if period_start is None and period_end is None:
        return month_period_for(clock.now())
    if period_start is None or period_end is None:
        raise UsageValidationError("from and to must be provided together")

    normalized_start = _normalize_datetime(period_start)
    normalized_end = _normalize_datetime(period_end)
    if normalized_end <= normalized_start:
        raise UsageValidationError("to must be after from")
    return normalized_start, normalized_end


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
