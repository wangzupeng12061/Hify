from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreateProviderRequest(BaseModel):
    provider_type: str = Field(pattern="^(openai|anthropic|gemini|ollama)$")
    name: str = Field(min_length=1, max_length=120)
    base_url: str | None = Field(default=None, max_length=500)
    credential_plaintext: str = Field(min_length=1, max_length=4096)


class ProviderResponse(BaseModel):
    id: UUID
    team_id: UUID
    provider_type: str
    name: str
    base_url: str | None
    status: str


class AddProviderModelRequest(BaseModel):
    model_name: str = Field(min_length=1, max_length=160)
    display_name: str = Field(min_length=1, max_length=160)
    kind: str = Field(pattern="^(chat|embedding)$")
    context_window_tokens: int = Field(ge=1)
    supports_tools: bool = False
    supports_vision: bool = False
    supports_structured_output: bool = False


class SetProviderModelPricingRequest(BaseModel):
    price_per_1m_input_tokens: Decimal | None = Field(default=None, ge=0)
    price_per_1m_output_tokens: Decimal | None = Field(default=None, ge=0)


class ModelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    team_id: UUID
    provider_id: UUID
    provider_type: str
    provider_name: str
    model_name: str
    display_name: str
    kind: str
    status: str
    context_window_tokens: int
    supports_tools: bool
    supports_vision: bool
    supports_structured_output: bool
    price_per_1m_input_tokens: Decimal | None
    price_per_1m_output_tokens: Decimal | None
