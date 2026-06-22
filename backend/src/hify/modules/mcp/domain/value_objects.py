from __future__ import annotations

from enum import StrEnum
from typing import Mapping

from hify.modules.mcp.domain.errors import McpValidationError


class McpServerStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


class McpToolStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


class McpTransport(StrEnum):
    STREAMABLE_HTTP = "streamable_http"


def normalize_server_name(value: str) -> str:
    normalized = " ".join(value.strip().split())
    if not normalized:
        raise McpValidationError("mcp server name must not be blank")
    if len(normalized) > 120:
        raise McpValidationError("mcp server name must be at most 120 characters")
    return normalized


def normalize_server_description(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.strip().split())
    if not normalized:
        return None
    if len(normalized) > 1000:
        raise McpValidationError("mcp server description must be at most 1000 characters")
    return normalized


def parse_transport(value: str) -> McpTransport:
    try:
        return McpTransport(value)
    except ValueError as exc:
        raise McpValidationError("mcp transport is invalid") from exc


def normalize_endpoint_url(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise McpValidationError("mcp endpoint url must not be blank")
    if len(normalized) > 1000:
        raise McpValidationError("mcp endpoint url must be at most 1000 characters")
    if not normalized.startswith("https://"):
        raise McpValidationError("mcp endpoint url must start with https://")
    return normalized


def normalize_tool_name(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise McpValidationError("mcp tool name must not be blank")
    if len(normalized) > 200:
        raise McpValidationError("mcp tool name must be at most 200 characters")
    return normalized


def normalize_tool_description(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.strip().split())
    if not normalized:
        return None
    if len(normalized) > 2000:
        raise McpValidationError("mcp tool description must be at most 2000 characters")
    return normalized


def normalize_input_schema(value: Mapping[str, object]) -> dict[str, object]:
    if value.get("type") != "object":
        raise McpValidationError("mcp tool input schema must be an object schema")
    return dict(value)
