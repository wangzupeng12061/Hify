from __future__ import annotations

from hify.modules.agents.domain.errors import AgentValidationError
from hify.modules.agents.domain.value_objects import ModelBindingSnapshot
from hify.modules.providers.contracts.dto import ModelInfo


def model_binding_snapshot_from_model_info(model: ModelInfo) -> ModelBindingSnapshot:
    if model.status != "active":
        raise AgentValidationError("provider model must be active")
    if model.kind != "chat":
        raise AgentValidationError("agent provider model must be a chat model")
    return ModelBindingSnapshot(
        provider_model_id=model.id,
        provider_type=model.provider_type,
        provider_name=model.provider_name,
        model_name=model.model_name,
        model_display_name=model.display_name,
        context_window_tokens=model.context_window_tokens,
        supports_tools=model.supports_tools,
        supports_vision=model.supports_vision,
        supports_structured_output=model.supports_structured_output,
    )
