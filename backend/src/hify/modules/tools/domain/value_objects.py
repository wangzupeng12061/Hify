from __future__ import annotations

from enum import StrEnum
from typing import Mapping

from hify.modules.tools.domain.errors import ToolValidationError


class ToolKind(StrEnum):
    BUILTIN = "builtin"
    HTTP = "http"
    MCP = "mcp"


class ToolStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


class HttpToolMethod(StrEnum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


def normalize_tool_name(value: str) -> str:
    normalized = " ".join(value.strip().split())
    if not normalized:
        raise ToolValidationError("tool name must not be blank")
    if len(normalized) > 120:
        raise ToolValidationError("tool name must be at most 120 characters")
    return normalized


def normalize_tool_description(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.strip().split())
    if not normalized:
        return None
    if len(normalized) > 1000:
        raise ToolValidationError("tool description must be at most 1000 characters")
    return normalized


def normalize_builtin_name(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if len(normalized) > 160:
        raise ToolValidationError("builtin tool name must be at most 160 characters")
    if not all(character.islower() or character.isdigit() or character in "._-" for character in normalized):
        raise ToolValidationError("builtin tool name must use lowercase letters, digits, dot, dash, or underscore")
    return normalized


def normalize_endpoint_url(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if len(normalized) > 1000:
        raise ToolValidationError("endpoint url must be at most 1000 characters")
    if not (normalized.startswith("http://") or normalized.startswith("https://")):
        raise ToolValidationError("endpoint url must start with http:// or https://")
    return normalized


def normalize_http_headers(value: Mapping[str, str] | None) -> dict[str, str]:
    if value is None:
        return {}
    if len(value) > 50:
        raise ToolValidationError("http headers must contain at most 50 entries")
    normalized: dict[str, str] = {}
    for header_name, header_value in value.items():
        normalized_name = header_name.strip()
        normalized_value = header_value.strip()
        if not normalized_name:
            raise ToolValidationError("http header name must not be blank")
        if len(normalized_name) > 120:
            raise ToolValidationError("http header name must be at most 120 characters")
        if len(normalized_value) > 1000:
            raise ToolValidationError("http header value must be at most 1000 characters")
        normalized[normalized_name] = normalized_value
    return normalized


def normalize_mcp_tool_name(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if len(normalized) > 200:
        raise ToolValidationError("mcp tool name must be at most 200 characters")
    return normalized


def normalize_input_schema(value: Mapping[str, object]) -> dict[str, object]:
    if "type" not in value:
        raise ToolValidationError("input schema must define a type")
    if value["type"] != "object":
        raise ToolValidationError("input schema type must be object")
    return dict(value)


def parse_tool_kind(value: str) -> ToolKind:
    try:
        return ToolKind(value)
    except ValueError as exc:
        raise ToolValidationError("tool kind is invalid") from exc


def parse_http_tool_method(value: str | None) -> HttpToolMethod | None:
    if value is None:
        return None
    try:
        return HttpToolMethod(value.upper())
    except ValueError as exc:
        raise ToolValidationError("http method is invalid") from exc
