import { hifyApiClient, unwrapApiResponse } from "@/lib/api/client";

import type {
  CreateMcpServerRequest,
  GetMcpServerInput,
  ListMcpToolsInput,
  McpServer,
  McpTool,
  RefreshMcpToolsInput,
} from "./types";

export async function createMcpServer(request: CreateMcpServerRequest): Promise<McpServer> {
  return unwrapApiResponse(
    await hifyApiClient.POST("/mcp/servers", {
      body: request,
    }),
  );
}

export async function listMcpServers(): Promise<McpServer[]> {
  return unwrapApiResponse(await hifyApiClient.GET("/mcp/servers"));
}

export async function getMcpServer(request: GetMcpServerInput): Promise<McpServer> {
  return unwrapApiResponse(
    await hifyApiClient.GET("/mcp/servers/{server_id}", {
      params: {
        path: {
          server_id: request.serverId,
        },
      },
    }),
  );
}

export async function listMcpTools(request: ListMcpToolsInput): Promise<McpTool[]> {
  return unwrapApiResponse(
    await hifyApiClient.GET("/mcp/servers/{server_id}/tools", {
      params: {
        path: {
          server_id: request.serverId,
        },
      },
    }),
  );
}

export async function refreshMcpTools(request: RefreshMcpToolsInput): Promise<McpTool[]> {
  return unwrapApiResponse(
    await hifyApiClient.POST("/mcp/servers/{server_id}/refresh-tools", {
      params: {
        path: {
          server_id: request.serverId,
        },
      },
    }),
  );
}
