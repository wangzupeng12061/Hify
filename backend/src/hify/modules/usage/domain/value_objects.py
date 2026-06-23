from __future__ import annotations

from decimal import Decimal

from hify.modules.usage.domain.errors import UsageValidationError

MAX_PROVIDER_LENGTH = 32
MAX_MODEL_NAME_LENGTH = 200
MAX_IDEMPOTENCY_KEY_LENGTH = 200


def normalize_provider(value: str) -> str:
    normalized = value.strip().lower()
    if not normalized:
        raise UsageValidationError("provider must not be blank")
    if len(normalized) > MAX_PROVIDER_LENGTH:
        raise UsageValidationError("provider is too long")
    return normalized


def normalize_model_name(value: str) -> str:
    normalized = " ".join(value.strip().split())
    if not normalized:
        raise UsageValidationError("model name must not be blank")
    if len(normalized) > MAX_MODEL_NAME_LENGTH:
        raise UsageValidationError("model name is too long")
    return normalized


def normalize_idempotency_key(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise UsageValidationError("idempotency key must not be blank")
    if len(normalized) > MAX_IDEMPOTENCY_KEY_LENGTH:
        raise UsageValidationError("idempotency key is too long")
    return normalized


def validate_tokens(value: int, field_name: str) -> int:
    if value < 0:
        raise UsageValidationError(f"{field_name} must be non-negative")
    return value


def validate_cost_amount(value: Decimal) -> Decimal:
    if value < Decimal("0"):
        raise UsageValidationError("cost amount must be non-negative")
    return value


def validate_monthly_token_limit(value: int | None) -> int | None:
    if value is None:
        return None
    if value <= 0:
        raise UsageValidationError("monthly token limit must be positive")
    return value
