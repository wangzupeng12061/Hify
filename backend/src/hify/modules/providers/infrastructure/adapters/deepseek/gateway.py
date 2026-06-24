from __future__ import annotations

from asyncio import CancelledError, TimeoutError, wait_for
from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass
import logging
from time import monotonic
from typing import Literal, Protocol, cast
from uuid import UUID

from openai import APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI

from hify.modules.providers.application.ports import ProvidersUnitOfWorkFactory
from hify.modules.providers.contracts.dto import (
    CallContext,
    DoneChunk,
    ModelChunk,
    ModelMessage,
    ModelRequest,
    ModelUsage,
    ReasoningDeltaChunk,
    TextDeltaChunk,
    ToolCallDeltaChunk,
    UsageChunk,
)
from hify.modules.providers.contracts.errors import (
    ProviderAuthenticationError,
    ProviderBadRequestError,
    ProviderCancelledError,
    ProviderContextLimitError,
    ProviderPermissionError,
    ProviderRateLimitError,
    ProviderStreamInterruptedError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from hify.modules.providers.contracts.services import ModelGateway
from hify.modules.providers.domain.entities import ModelProvider, ProviderCredential, ProviderModel
from hify.modules.providers.domain.value_objects import (
    CredentialSecret,
    CredentialStatus,
    ModelKind,
    ModelStatus,
    ProviderStatus,
    ProviderType,
)
from hify.shared.domain.ids import new_uuid

logger = logging.getLogger(__name__)

DEEPSEEK_DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_FIRST_TOKEN_TIMEOUT_SECONDS = 45.0
DEFAULT_STREAM_IDLE_TIMEOUT_SECONDS = 60.0


class CredentialDecryptorProtocol(Protocol):
    def decrypt(self, secret: CredentialSecret) -> str: ...


@dataclass(frozen=True, slots=True)
class DeepSeekRuntimeModel:
    provider_id: UUID
    credential_fingerprint: str
    base_url: str
    model_name: str
    api_key: str


@dataclass(frozen=True, slots=True)
class DeepSeekClientKey:
    provider_id: UUID
    base_url: str
    credential_fingerprint: str


@dataclass(slots=True)
class _ToolCallState:
    tool_call_id: str
    name: str


class DeepSeekClientRegistry:
    def __init__(self) -> None:
        self._clients: dict[DeepSeekClientKey, AsyncOpenAI] = {}

    def get_client(self, runtime_model: DeepSeekRuntimeModel) -> AsyncOpenAI:
        key = DeepSeekClientKey(
            provider_id=runtime_model.provider_id,
            base_url=runtime_model.base_url,
            credential_fingerprint=runtime_model.credential_fingerprint,
        )
        client = self._clients.get(key)
        if client is None:
            client = AsyncOpenAI(
                api_key=runtime_model.api_key,
                base_url=runtime_model.base_url,
                max_retries=0,
            )
            self._clients[key] = client
        return client

    async def close(self) -> None:
        for client in self._clients.values():
            await client.close()
        self._clients.clear()


class DeepSeekModelGateway(ModelGateway):
    def __init__(
        self,
        unit_of_work_factory: ProvidersUnitOfWorkFactory,
        credential_decryptor: CredentialDecryptorProtocol,
        *,
        client_registry: DeepSeekClientRegistry | None = None,
        first_token_timeout_seconds: float = DEFAULT_FIRST_TOKEN_TIMEOUT_SECONDS,
        stream_idle_timeout_seconds: float = DEFAULT_STREAM_IDLE_TIMEOUT_SECONDS,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._credential_decryptor = credential_decryptor
        self._client_registry = client_registry or DeepSeekClientRegistry()
        self._first_token_timeout_seconds = first_token_timeout_seconds
        self._stream_idle_timeout_seconds = stream_idle_timeout_seconds

    def stream(
        self,
        request: ModelRequest,
        context: CallContext,
    ) -> AsyncIterator[ModelChunk]:
        return self._stream(request, context)

    async def _stream(
        self,
        request: ModelRequest,
        context: CallContext,
    ) -> AsyncIterator[ModelChunk]:
        runtime_model = await self._load_runtime_model(request, context)
        client = self._client_registry.get_client(runtime_model)
        content_emitted = False
        done_emitted = False
        tool_calls: dict[int, _ToolCallState] = {}

        try:
            stream = await client.chat.completions.create(  # type: ignore[call-overload]
                **_chat_completion_request(runtime_model.model_name, request),
            )
            stream_iterator = stream.__aiter__()

            while True:
                context.cancellation.raise_if_cancelled()
                timeout_seconds = _bounded_timeout_seconds(
                    context,
                    (
                        self._stream_idle_timeout_seconds
                        if content_emitted
                        else self._first_token_timeout_seconds
                    ),
                    timeout_stage="stream_idle" if content_emitted else "first_token",
                )
                try:
                    chunk = await wait_for(stream_iterator.__anext__(), timeout=timeout_seconds)
                except StopAsyncIteration:
                    break
                except TimeoutError as exc:
                    raise ProviderTimeoutError(
                        "deepseek model stream timed out",
                        timeout_stage="stream_idle" if content_emitted else "first_token",
                    ) from exc

                usage_chunk = _usage_chunk(chunk)
                if usage_chunk is not None:
                    yield usage_chunk

                for model_chunk in _model_chunks_from_stream_chunk(chunk, tool_calls):
                    if isinstance(model_chunk, DoneChunk):
                        done_emitted = True
                    else:
                        content_emitted = True
                    yield model_chunk

            if not done_emitted:
                yield DoneChunk(chunk_type="done", finish_reason="stop")
        except ProviderTimeoutError as exc:
            if content_emitted:
                raise ProviderStreamInterruptedError("deepseek model stream timed out") from exc
            raise
        except ProviderCancelledError:
            raise
        except CancelledError:
            raise
        except (APIConnectionError, APITimeoutError, APIStatusError) as exc:
            if content_emitted:
                raise ProviderStreamInterruptedError("deepseek model stream interrupted") from exc
            raise _provider_error_from_openai_error(exc) from exc

    async def _load_runtime_model(
        self,
        request: ModelRequest,
        context: CallContext,
    ) -> DeepSeekRuntimeModel:
        async with self._unit_of_work_factory() as unit_of_work:
            model = await unit_of_work.models.get_by_id(request.model_id)
            if model is None or model.team_id != context.team_id:
                raise ProviderBadRequestError("provider model was not found")
            provider = await unit_of_work.providers.get_by_id(model.provider_id)
            if provider is None or provider.team_id != context.team_id:
                raise ProviderBadRequestError("provider model was not found")
            credential = await unit_of_work.credentials.get_by_provider_id(provider.id)

        _validate_runtime_model(provider, model, credential)
        if credential is None:
            raise ProviderAuthenticationError("deepseek provider credential is missing")

        return DeepSeekRuntimeModel(
            provider_id=provider.id,
            credential_fingerprint=credential.secret.fingerprint,
            base_url=provider.base_url or DEEPSEEK_DEFAULT_BASE_URL,
            model_name=model.model_name,
            api_key=self._credential_decryptor.decrypt(credential.secret),
        )


def _validate_runtime_model(
    provider: ModelProvider,
    model: ProviderModel,
    credential: ProviderCredential | None,
) -> None:
    if provider.provider_type is not ProviderType.DEEPSEEK:
        raise ProviderBadRequestError("provider model is not a deepseek model")
    if provider.status is not ProviderStatus.ACTIVE:
        raise ProviderUnavailableError("deepseek provider is disabled")
    if model.kind is not ModelKind.CHAT:
        raise ProviderBadRequestError("deepseek runtime supports chat models only")
    if model.status is not ModelStatus.ACTIVE:
        raise ProviderUnavailableError("deepseek model is disabled")
    if credential is None:
        return
    if credential.status is not CredentialStatus.ACTIVE:
        raise ProviderAuthenticationError("deepseek provider credential is disabled")


def _chat_completion_request(
    model_name: str,
    request: ModelRequest,
) -> dict[str, object]:
    body: dict[str, object] = {
        "model": model_name,
        "messages": _openai_messages(request),
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    if request.temperature is not None:
        body["temperature"] = request.temperature
    if request.max_output_tokens is not None:
        body["max_tokens"] = request.max_output_tokens
    if request.tools:
        body["tools"] = [dict(tool) for tool in request.tools]
    return body


def _openai_messages(request: ModelRequest) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    if request.system_prompt:
        messages.append({"role": "system", "content": request.system_prompt})
    for message in request.messages:
        messages.append(_openai_message(message))
    return messages


def _openai_message(message: ModelMessage) -> dict[str, str]:
    if message.role == "tool":
        return {"role": "user", "content": f"Tool result:\n{message.content}"}
    return {"role": message.role, "content": message.content}


def _model_chunks_from_stream_chunk(
    chunk: object,
    tool_calls: dict[int, _ToolCallState],
) -> tuple[ModelChunk, ...]:
    chunks: list[ModelChunk] = []
    for choice in cast(tuple[object, ...], tuple(getattr(chunk, "choices", ()) or ())):
        delta = getattr(choice, "delta", None)
        if delta is not None:
            content = getattr(delta, "content", None)
            if isinstance(content, str) and content:
                chunks.append(TextDeltaChunk(chunk_type="text_delta", text=content))

            reasoning_content = getattr(delta, "reasoning_content", None)
            if isinstance(reasoning_content, str) and reasoning_content:
                chunks.append(
                    ReasoningDeltaChunk(chunk_type="reasoning_delta", text=reasoning_content)
                )

            for tool_call in cast(tuple[object, ...], tuple(getattr(delta, "tool_calls", ()) or ())):
                tool_chunk = _tool_call_delta_chunk(tool_call, tool_calls)
                if tool_chunk is not None:
                    chunks.append(tool_chunk)

        finish_reason = _finish_reason(getattr(choice, "finish_reason", None))
        if finish_reason is not None:
            chunks.append(DoneChunk(chunk_type="done", finish_reason=finish_reason))
    return tuple(chunks)


def _tool_call_delta_chunk(
    tool_call: object,
    tool_calls: dict[int, _ToolCallState],
) -> ToolCallDeltaChunk | None:
    index = getattr(tool_call, "index", None)
    if not isinstance(index, int):
        index = len(tool_calls)
    state = tool_calls.get(index)
    if state is None:
        state = _ToolCallState(tool_call_id=str(new_uuid()), name="")
        tool_calls[index] = state

    function = getattr(tool_call, "function", None)
    name = getattr(function, "name", None) if function is not None else None
    arguments = getattr(function, "arguments", None) if function is not None else None
    if isinstance(name, str) and name:
        state.name = name
    arguments_delta = arguments if isinstance(arguments, str) else ""
    if not state.name and not arguments_delta:
        return None
    return ToolCallDeltaChunk(
        chunk_type="tool_call_delta",
        tool_call_id=state.tool_call_id,
        name=state.name,
        arguments_delta=arguments_delta,
    )


def _usage_chunk(chunk: object) -> UsageChunk | None:
    usage = getattr(chunk, "usage", None)
    if usage is None:
        return None
    prompt_tokens = getattr(usage, "prompt_tokens", None)
    completion_tokens = getattr(usage, "completion_tokens", None)
    if not isinstance(prompt_tokens, int) or not isinstance(completion_tokens, int):
        return None
    return UsageChunk(
        chunk_type="usage",
        usage=ModelUsage(input_tokens=prompt_tokens, output_tokens=completion_tokens),
    )


def _finish_reason(value: object) -> Literal[
    "stop",
    "length",
    "tool_calls",
    "content_filter",
    "cancelled",
] | None:
    if value is None:
        return None
    if value in {"stop", "length", "tool_calls", "content_filter"}:
        return cast(
            Literal["stop", "length", "tool_calls", "content_filter"],
            value,
        )
    logger.warning("unknown deepseek finish reason", extra={"event": "provider.finish_unknown"})
    return "stop"


def _bounded_timeout_seconds(
    context: CallContext,
    configured_seconds: float,
    *,
    timeout_stage: str,
) -> float:
    remaining_seconds = context.deadline - monotonic()
    if remaining_seconds <= 0:
        raise ProviderTimeoutError("model call deadline exceeded", timeout_stage="deadline")
    timeout_seconds = min(configured_seconds, remaining_seconds)
    if timeout_seconds <= 0:
        raise ProviderTimeoutError(
            "model call timeout budget exhausted",
            timeout_stage=timeout_stage,
        )
    return timeout_seconds


def _provider_error_from_openai_error(
    error: APIConnectionError | APITimeoutError | APIStatusError,
) -> Exception:
    if isinstance(error, APITimeoutError):
        return ProviderTimeoutError("deepseek request timed out", timeout_stage="request")
    if isinstance(error, APIConnectionError):
        return ProviderUnavailableError("deepseek provider is unavailable")

    status_code = error.status_code
    if status_code == 401:
        return ProviderAuthenticationError("deepseek authentication failed")
    if status_code == 403:
        return ProviderPermissionError("deepseek permission denied")
    if status_code == 408:
        return ProviderTimeoutError("deepseek request timed out", timeout_stage="request")
    if status_code == 429:
        retry_after = _retry_after_seconds(error.response.headers)
        return ProviderRateLimitError("deepseek rate limit exceeded", retry_after_seconds=retry_after)
    if status_code in {500, 502, 503, 504}:
        return ProviderUnavailableError("deepseek provider is unavailable")
    if status_code == 400 and _looks_like_context_limit(error):
        return ProviderContextLimitError("deepseek context limit exceeded")
    return ProviderBadRequestError("deepseek request was rejected")


def _looks_like_context_limit(error: APIStatusError) -> bool:
    text = str(error).lower()
    return "context" in text or "maximum context" in text or "token" in text


def _retry_after_seconds(headers: Mapping[str, str]) -> float | None:
    value = headers.get("retry-after")
    if value is None:
        return None
    try:
        parsed = float(value)
    except ValueError:
        return None
    if parsed < 0:
        return None
    return parsed
