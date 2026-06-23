"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createMcpServer,
  getMcpServer,
  listMcpServers,
  listMcpTools,
  refreshMcpTools,
} from "./api";
import type { GetMcpServerInput, ListMcpToolsInput } from "./types";

export const mcpQueryKeys = {
  all: ["mcp"] as const,
  detail: (request: GetMcpServerInput) => [...mcpQueryKeys.all, "detail", request.serverId] as const,
  list: () => [...mcpQueryKeys.all, "list"] as const,
  tools: (request: ListMcpToolsInput) => [...mcpQueryKeys.all, "tools", request.serverId] as const,
};

export const mcpMutationKeys = {
  createServer: ["mcp", "create-server"] as const,
  refreshTools: ["mcp", "refresh-tools"] as const,
};

export function useCreateMcpServer() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createMcpServer,
    mutationKey: mcpMutationKeys.createServer,
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: mcpQueryKeys.list(),
      });
    },
  });
}

export function useMcpServers() {
  return useQuery({
    queryFn: listMcpServers,
    queryKey: mcpQueryKeys.list(),
  });
}

export function useMcpServer(request: GetMcpServerInput | null) {
  return useQuery({
    enabled: request !== null,
    queryFn: () => {
      if (request === null) {
        throw new Error("MCP server query requires a server ID.");
      }

      return getMcpServer(request);
    },
    queryKey:
      request === null ? [...mcpQueryKeys.all, "detail", "idle"] : mcpQueryKeys.detail(request),
  });
}

export function useMcpTools(request: ListMcpToolsInput | null) {
  return useQuery({
    enabled: request !== null,
    queryFn: () => {
      if (request === null) {
        throw new Error("MCP tools query requires a server ID.");
      }

      return listMcpTools(request);
    },
    queryKey:
      request === null ? [...mcpQueryKeys.all, "tools", "idle"] : mcpQueryKeys.tools(request),
  });
}

export function useRefreshMcpTools() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: refreshMcpTools,
    mutationKey: mcpMutationKeys.refreshTools,
    onSuccess: async (_tools, request) => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: mcpQueryKeys.detail({ serverId: request.serverId }),
        }),
        queryClient.invalidateQueries({
          queryKey: mcpQueryKeys.tools({ serverId: request.serverId }),
        }),
        queryClient.invalidateQueries({
          queryKey: mcpQueryKeys.list(),
        }),
      ]);
    },
  });
}
