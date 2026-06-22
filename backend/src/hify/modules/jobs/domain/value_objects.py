from __future__ import annotations

from enum import StrEnum
from typing import Mapping

from hify.modules.jobs.domain.errors import JobValidationError


MAX_IDEMPOTENCY_KEY_LENGTH = 160
MAX_JOB_KIND_LENGTH = 120
MAX_LEASE_OWNER_LENGTH = 120
MAX_ERROR_CODE_LENGTH = 120
MAX_ERROR_MESSAGE_LENGTH = 1000
MAX_JOB_PAYLOAD_KEYS = 100
MAX_JOB_ATTEMPTS = 10


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobQueue(StrEnum):
    INGESTION = "ingestion"
    EMBEDDING = "embedding"
    LLM_BATCH = "llm_batch"
    EVENTS = "events"
    MAINTENANCE = "maintenance"


def normalize_job_queue(value: str) -> JobQueue:
    try:
        return JobQueue(value.strip())
    except ValueError as exc:
        raise JobValidationError("job queue is not supported") from exc


def normalize_idempotency_key(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise JobValidationError("job idempotency key must not be blank")
    if len(normalized) > MAX_IDEMPOTENCY_KEY_LENGTH:
        raise JobValidationError("job idempotency key is too long")
    return normalized


def normalize_job_kind(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise JobValidationError("job kind must not be blank")
    if len(normalized) > MAX_JOB_KIND_LENGTH:
        raise JobValidationError("job kind is too long")
    return normalized


def normalize_lease_owner(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise JobValidationError("job lease owner must not be blank")
    if len(normalized) > MAX_LEASE_OWNER_LENGTH:
        raise JobValidationError("job lease owner is too long")
    return normalized


def normalize_error_code(value: str) -> str:
    normalized = value.strip().upper()
    if not normalized:
        raise JobValidationError("job error code must not be blank")
    if len(normalized) > MAX_ERROR_CODE_LENGTH:
        raise JobValidationError("job error code is too long")
    return normalized


def normalize_error_message(value: str) -> str:
    normalized = " ".join(value.strip().split())
    if not normalized:
        raise JobValidationError("job error message must not be blank")
    if len(normalized) > MAX_ERROR_MESSAGE_LENGTH:
        return normalized[:MAX_ERROR_MESSAGE_LENGTH]
    return normalized


def normalize_payload(value: Mapping[str, object]) -> dict[str, object]:
    if len(value) > MAX_JOB_PAYLOAD_KEYS:
        raise JobValidationError("job payload has too many fields")
    return dict(value)


def validate_max_attempts(value: int) -> None:
    if value < 1 or value > MAX_JOB_ATTEMPTS:
        raise JobValidationError(f"job max attempts must be between 1 and {MAX_JOB_ATTEMPTS}")
