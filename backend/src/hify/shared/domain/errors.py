from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True, slots=True)
class ErrorDetail:
    code: str
    message: str
    metadata: Mapping[str, object] | None = None


class HifyError(Exception):
    code = "HIFY_ERROR"

    def __init__(self, message: str, *, metadata: Mapping[str, object] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.metadata = metadata

    def to_detail(self) -> ErrorDetail:
        return ErrorDetail(code=self.code, message=self.message, metadata=self.metadata)


class ValidationError(HifyError):
    code = "VALIDATION_ERROR"


class NotFoundError(HifyError):
    code = "NOT_FOUND"


class ConflictError(HifyError):
    code = "CONFLICT"


class PermissionDeniedError(HifyError):
    code = "PERMISSION_DENIED"
