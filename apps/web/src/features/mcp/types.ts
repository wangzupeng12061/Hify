import type { components } from "@/lib/api/generated/schema";

export type CreateMcpServerRequest = components["schemas"]["CreateMcpServerRequest"];
export type McpServer = components["schemas"]["McpServerResponse"];
export type McpTool = components["schemas"]["McpToolResponse"];

export type GetMcpServerInput = {
  serverId: string;
};

export type ListMcpToolsInput = {
  serverId: string;
};

export type RefreshMcpToolsInput = {
  serverId: string;
};
