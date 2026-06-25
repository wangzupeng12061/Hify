from __future__ import annotations

from collections.abc import Mapping
from typing import cast
import json

import httpx

from hify.modules.tools.application.ports import BuiltinToolInvocation
from hify.modules.tools.contracts.dto import ToolExecutionResult
from hify.modules.tools.domain.errors import (
    ToolExecutionHttpError,
    ToolExecutionTimeoutError,
    ToolValidationError,
)

WEB_SEARCH_BUILTIN_NAME = "web.search"
WEB_SEARCH_INPUT_SCHEMA: Mapping[str, object] = {
    "type": "object",
    "required": ["query"],
    "properties": {
        "query": {
            "type": "string",
            "description": "Search query for current public web information.",
        },
        "max_results": {
            "type": "integer",
            "description": "Maximum number of results to return. Defaults to 5.",
        },
    },
}
DEFAULT_WEB_SEARCH_TIMEOUT_SECONDS = 10.0
DEFAULT_WEB_SEARCH_MAX_RESULTS = 5
MAX_WEB_SEARCH_RESULTS = 8


class DuckDuckGoWebSearchTool:
    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        *,
        timeout_seconds: float = DEFAULT_WEB_SEARCH_TIMEOUT_SECONDS,
        default_max_results: int = DEFAULT_WEB_SEARCH_MAX_RESULTS,
    ) -> None:
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(timeout_seconds),
            follow_redirects=False,
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        )
        self._default_max_results = _bounded_max_results(default_max_results)

    async def invoke(self, invocation: BuiltinToolInvocation) -> ToolExecutionResult:
        query = _required_string(invocation.arguments, "query")
        max_results = _optional_max_results(invocation.arguments, self._default_max_results)
        try:
            response = await self._client.get(
                "https://api.duckduckgo.com/",
                params={
                    "q": query,
                    "format": "json",
                    "no_html": "1",
                    "skip_disambig": "1",
                },
            )
        except httpx.TimeoutException as exc:
            raise ToolExecutionTimeoutError("web search timed out") from exc
        except httpx.HTTPError as exc:
            raise ToolExecutionHttpError("web search request failed") from exc

        if response.status_code >= 400:
            raise ToolExecutionHttpError(
                "web search returned an error status",
                metadata={"status_code": response.status_code},
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise ToolExecutionHttpError("web search returned invalid json") from exc

        if not isinstance(payload, dict):
            raise ToolExecutionHttpError("web search returned invalid payload")

        results = _search_results(payload, max_results)
        answer = _optional_string(payload.get("AbstractText"))
        heading = _optional_string(payload.get("Heading"))
        content = {
            "query": query,
            "answer": answer,
            "heading": heading,
            "results": results,
        }
        return ToolExecutionResult(
            tool_call_id=invocation.tool_call_id,
            content=json.dumps(content, ensure_ascii=False),
            metadata={
                "provider": "duckduckgo",
                "result_count": len(results),
                "has_answer": answer is not None,
            },
        )


def _required_string(arguments: Mapping[str, object], field_name: str) -> str:
    value = arguments.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ToolValidationError(
            "web search query is required",
            metadata={"field": field_name},
        )
    return " ".join(value.strip().split())


def _optional_max_results(arguments: Mapping[str, object], default_value: int) -> int:
    value = arguments.get("max_results")
    if value is None:
        return default_value
    if not isinstance(value, int) or isinstance(value, bool):
        raise ToolValidationError(
            "web search max_results must be an integer",
            metadata={"field": "max_results"},
        )
    return _bounded_max_results(value)


def _bounded_max_results(value: int) -> int:
    if value < 1:
        return 1
    return min(value, MAX_WEB_SEARCH_RESULTS)


def _search_results(payload: Mapping[str, object], max_results: int) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []

    abstract_url = _optional_string(payload.get("AbstractURL"))
    abstract_text = _optional_string(payload.get("AbstractText"))
    heading = _optional_string(payload.get("Heading"))
    if abstract_url is not None and abstract_text is not None:
        results.append(
            {
                "title": heading or abstract_url,
                "url": abstract_url,
                "snippet": abstract_text,
            }
        )

    related_topics = payload.get("RelatedTopics")
    if isinstance(related_topics, list):
        _append_related_topics(results, related_topics, max_results)

    return results[:max_results]


def _append_related_topics(
    results: list[dict[str, str]],
    related_topics: list[object],
    max_results: int,
) -> None:
    for topic in related_topics:
        if len(results) >= max_results:
            return
        if not isinstance(topic, dict):
            continue
        nested_topics = topic.get("Topics")
        if isinstance(nested_topics, list):
            _append_related_topics(results, nested_topics, max_results)
            continue

        first_url = _optional_string(topic.get("FirstURL"))
        text = _optional_string(topic.get("Text"))
        if first_url is None or text is None:
            continue
        results.append(
            {
                "title": _title_from_text(text),
                "url": first_url,
                "snippet": text,
            }
        )


def _optional_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = " ".join(value.strip().split())
    return normalized or None


def _title_from_text(value: str) -> str:
    first_part = value.split(" - ", 1)[0].strip()
    if first_part:
        return first_part[:120]
    return cast(str, value[:120])
