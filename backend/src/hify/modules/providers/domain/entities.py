from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from hify.shared.domain.ids import new_uuid

from hify.modules.providers.domain.errors import ProviderValidationError
from hify.modules.providers.domain.value_objects import (
    CredentialSecret,
    CredentialStatus,
    ModelKind,
    ModelStatus,
    ProviderStatus,
    ProviderType,
    normalize_base_url,
    normalize_display_name,
    normalize_model_name,
    normalize_provider_name,
    validate_model_price,
)


@dataclass(slots=True)
class ModelProvider:
    id: UUID
    team_id: UUID
    provider_type: ProviderType
    name: str
    base_url: str | None
    status: ProviderStatus
    version: int
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        team_id: UUID,
        provider_type: ProviderType,
        name: str,
        base_url: str | None,
        created_by: UUID,
        now: datetime,
    ) -> ModelProvider:
        return cls(
            id=new_uuid(),
            team_id=team_id,
            provider_type=provider_type,
            name=normalize_provider_name(name),
            base_url=normalize_base_url(base_url),
            status=ProviderStatus.ACTIVE,
            version=0,
            created_by=created_by,
            created_at=now,
            updated_at=now,
        )

    def disable(self, *, now: datetime) -> None:
        if self.status == ProviderStatus.DISABLED:
            return
        self.status = ProviderStatus.DISABLED
        self._mark_updated(now)

    def _mark_updated(self, now: datetime) -> None:
        self.version += 1
        self.updated_at = now


@dataclass(slots=True)
class ProviderCredential:
    id: UUID
    team_id: UUID
    provider_id: UUID
    secret: CredentialSecret
    status: CredentialStatus
    version: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        team_id: UUID,
        provider_id: UUID,
        secret: CredentialSecret,
        now: datetime,
    ) -> ProviderCredential:
        return cls(
            id=new_uuid(),
            team_id=team_id,
            provider_id=provider_id,
            secret=secret,
            status=CredentialStatus.ACTIVE,
            version=0,
            created_at=now,
            updated_at=now,
        )

    def rotate(self, secret: CredentialSecret, *, now: datetime) -> None:
        self.secret = secret
        self.status = CredentialStatus.ACTIVE
        self._mark_updated(now)

    def disable(self, *, now: datetime) -> None:
        if self.status == CredentialStatus.DISABLED:
            return
        self.status = CredentialStatus.DISABLED
        self._mark_updated(now)

    def _mark_updated(self, now: datetime) -> None:
        self.version += 1
        self.updated_at = now


@dataclass(slots=True)
class ProviderModel:
    id: UUID
    team_id: UUID
    provider_id: UUID
    model_name: str
    display_name: str
    kind: ModelKind
    status: ModelStatus
    context_window_tokens: int
    supports_tools: bool
    supports_vision: bool
    supports_structured_output: bool
    price_per_1m_input_tokens: Decimal | None
    price_per_1m_output_tokens: Decimal | None
    version: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        team_id: UUID,
        provider_id: UUID,
        model_name: str,
        display_name: str,
        kind: ModelKind,
        context_window_tokens: int,
        supports_tools: bool,
        supports_vision: bool,
        supports_structured_output: bool,
        now: datetime,
    ) -> ProviderModel:
        if context_window_tokens < 1:
            raise ProviderValidationError("context window tokens must be positive")
        return cls(
            id=new_uuid(),
            team_id=team_id,
            provider_id=provider_id,
            model_name=normalize_model_name(model_name),
            display_name=normalize_display_name(display_name),
            kind=kind,
            status=ModelStatus.ACTIVE,
            context_window_tokens=context_window_tokens,
            supports_tools=supports_tools,
            supports_vision=supports_vision,
            supports_structured_output=supports_structured_output,
            price_per_1m_input_tokens=None,
            price_per_1m_output_tokens=None,
            version=0,
            created_at=now,
            updated_at=now,
        )

    def set_pricing(
        self,
        *,
        price_per_1m_input_tokens: Decimal | None,
        price_per_1m_output_tokens: Decimal | None,
        now: datetime,
    ) -> None:
        self.price_per_1m_input_tokens = validate_model_price(
            price_per_1m_input_tokens,
            "price_per_1m_input_tokens",
        )
        self.price_per_1m_output_tokens = validate_model_price(
            price_per_1m_output_tokens,
            "price_per_1m_output_tokens",
        )
        self._mark_updated(now)

    def update_configuration(
        self,
        *,
        display_name: str,
        context_window_tokens: int,
        supports_tools: bool,
        supports_vision: bool,
        supports_structured_output: bool,
        now: datetime,
    ) -> None:
        if context_window_tokens < 1:
            raise ProviderValidationError("context window tokens must be positive")
        self.display_name = normalize_display_name(display_name)
        self.context_window_tokens = context_window_tokens
        self.supports_tools = supports_tools
        self.supports_vision = supports_vision
        self.supports_structured_output = supports_structured_output
        self._mark_updated(now)

    def disable(self, *, now: datetime) -> None:
        if self.status == ModelStatus.DISABLED:
            return
        self.status = ModelStatus.DISABLED
        self._mark_updated(now)

    def _mark_updated(self, now: datetime) -> None:
        self.version += 1
        self.updated_at = now
