from __future__ import annotations

from hify.shared.domain.errors import ConflictError, HifyError, NotFoundError, PermissionDeniedError, ValidationError


class McpValidationError(ValidationError):
    code = "MCP_VALIDATION_ERROR"


class McpServerNotFoundError(NotFoundError):
    code = "MCP_SERVER_NOT_FOUND"


class McpServerAlreadyExistsError(ConflictError):
    code = "MCP_SERVER_ALREADY_EXISTS"


class McpToolNotFoundError(NotFoundError):
    code = "MCP_TOOL_NOT_FOUND"


class McpPermissionDeniedError(PermissionDeniedError):
    code = "MCP_PERMISSION_DENIED"


class McpClientError(HifyError):
    code = "MCP_CLIENT_ERROR"


class McpClientNotConfiguredError(McpClientError):
    code = "MCP_CLIENT_NOT_CONFIGURED"
