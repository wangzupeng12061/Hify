from __future__ import annotations

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.mcp.domain.errors import McpPermissionDeniedError


MANAGE_MCP_PERMISSION = "mcp.manage"
READ_MCP_PERMISSION = "mcp.read"


def require_manage_mcp(actor: ActorContext) -> None:
    if not actor.has_permission(MANAGE_MCP_PERMISSION):
        raise McpPermissionDeniedError("actor does not have permission to manage mcp servers")


def require_read_mcp(actor: ActorContext) -> None:
    if not actor.has_permission(READ_MCP_PERMISSION):
        raise McpPermissionDeniedError("actor does not have permission to read mcp servers")
