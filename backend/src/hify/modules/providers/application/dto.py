from __future__ import annotations

from hify.modules.providers.contracts.dto import ModelInfo, ProviderInfo
from hify.modules.providers.domain.entities import ModelProvider, ProviderModel


def provider_info_from_domain(provider: ModelProvider) -> ProviderInfo:
    return ProviderInfo(
        id=provider.id,
        team_id=provider.team_id,
        provider_type=provider.provider_type.value,
        name=provider.name,
        base_url=provider.base_url,
        status=provider.status.value,
        created_at=provider.created_at,
        updated_at=provider.updated_at,
    )


def model_info_from_domain(provider: ModelProvider, model: ProviderModel) -> ModelInfo:
    return ModelInfo(
        id=model.id,
        team_id=model.team_id,
        provider_id=provider.id,
        provider_type=provider.provider_type.value,
        provider_name=provider.name,
        model_name=model.model_name,
        display_name=model.display_name,
        kind=model.kind.value,
        status=model.status.value,
        context_window_tokens=model.context_window_tokens,
        supports_tools=model.supports_tools,
        supports_vision=model.supports_vision,
        supports_structured_output=model.supports_structured_output,
        price_per_1m_input_tokens=model.price_per_1m_input_tokens,
        price_per_1m_output_tokens=model.price_per_1m_output_tokens,
    )
