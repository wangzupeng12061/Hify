from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from hify.modules.providers.domain.errors import ProviderValidationError


class ProviderType(StrEnum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    OLLAMA = "ollama"


class ProviderStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


class CredentialStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


class ModelStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


class ModelKind(StrEnum):
    CHAT = "chat"
    EMBEDDING = "embedding"


@dataclass(frozen=True, slots=True)
class CredentialSecret:
    ciphertext: bytes
    key_version: int
    fingerprint: str

    def __post_init__(self) -> None:
        if not self.ciphertext:
            raise ProviderValidationError("credential ciphertext must not be empty")
        if self.key_version < 1:
            raise ProviderValidationError("credential key version must be positive")
        if not self.fingerprint.strip():
            raise ProviderValidationError("credential fingerprint must not be blank")


def normalize_provider_name(value: str) -> str:
    normalized = " ".join(value.strip().split())
    if not normalized:
        raise ProviderValidationError("provider name must not be blank")
    if len(normalized) > 120:
        raise ProviderValidationError("provider name must be at most 120 characters")
    return normalized


def normalize_model_name(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ProviderValidationError("model name must not be blank")
    if len(normalized) > 160:
        raise ProviderValidationError("model name must be at most 160 characters")
    return normalized


def normalize_display_name(value: str) -> str:
    normalized = " ".join(value.strip().split())
    if not normalized:
        raise ProviderValidationError("display name must not be blank")
    if len(normalized) > 160:
        raise ProviderValidationError("display name must be at most 160 characters")
    return normalized


def normalize_base_url(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().rstrip("/")
    if not normalized:
        return None
    if len(normalized) > 500:
        raise ProviderValidationError("base url must be at most 500 characters")
    if not (normalized.startswith("http://") or normalized.startswith("https://")):
        raise ProviderValidationError("base url must start with http:// or https://")
    return normalized


def parse_provider_type(value: str) -> ProviderType:
    try:
        return ProviderType(value)
    except ValueError as exc:
        raise ProviderValidationError("provider type is invalid") from exc


def parse_model_kind(value: str) -> ModelKind:
    try:
        return ModelKind(value)
    except ValueError as exc:
        raise ProviderValidationError("model kind is invalid") from exc
