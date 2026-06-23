import { QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  useCreateMcpServer,
  useMcpServer,
  useMcpServers,
  useMcpTools,
  useRefreshMcpTools,
} from "@/features/mcp";
import { hifyApiClient } from "@/lib/api/client";
import { createHifyQueryClient } from "@/lib/query/query-client";

const apiClientMock = vi.hoisted(() => ({
  GET: vi.fn(),
  POST: vi.fn(),
}));

vi.mock("@/lib/api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/client")>();

  return {
    ...actual,
    hifyApiClient: apiClientMock,
  };
});

describe("mcp hooks", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("lists MCP servers", async () => {
    apiClientMock.GET.mockResolvedValueOnce({
      data: [createMcpServerResponse()],
      response: new Response(null, { status: 200 }),
    });

    const { result } = renderHook(() => useMcpServers(), {
      wrapper: createQueryWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(hifyApiClient.GET).toHaveBeenCalledWith("/mcp/servers");
    expect(result.current.data?.[0]?.id).toBe("mcp-server-1");
  });

  it("creates MCP servers with the backend request contract", async () => {
    apiClientMock.POST.mockResolvedValueOnce({
      data: createMcpServerResponse(),
      response: new Response(null, { status: 201 }),
    });

    const { result } = renderHook(() => useCreateMcpServer(), {
      wrapper: createQueryWrapper(),
    });

    const server = await result.current.mutateAsync({
      description: "Team MCP server",
      endpoint_url: "https://mcp.example.com/mcp",
      name: "Docs MCP",
      transport: "streamable_http",
    });

    expect(hifyApiClient.POST).toHaveBeenCalledWith("/mcp/servers", {
      body: {
        description: "Team MCP server",
        endpoint_url: "https://mcp.example.com/mcp",
        name: "Docs MCP",
        transport: "streamable_http",
      },
    });
    expect(server.id).toBe("mcp-server-1");
  });

  it("gets MCP server details with path params", async () => {
    apiClientMock.GET.mockResolvedValueOnce({
      data: createMcpServerResponse(),
      response: new Response(null, { status: 200 }),
    });

    const { result } = renderHook(() => useMcpServer({ serverId: "mcp-server-1" }), {
      wrapper: createQueryWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(hifyApiClient.GET).toHaveBeenCalledWith("/mcp/servers/{server_id}", {
      params: {
        path: {
          server_id: "mcp-server-1",
        },
      },
    });
  });

  it("lists MCP tools with path params", async () => {
    apiClientMock.GET.mockResolvedValueOnce({
      data: [createMcpToolResponse()],
      response: new Response(null, { status: 200 }),
    });

    const { result } = renderHook(() => useMcpTools({ serverId: "mcp-server-1" }), {
      wrapper: createQueryWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(hifyApiClient.GET).toHaveBeenCalledWith("/mcp/servers/{server_id}/tools", {
      params: {
        path: {
          server_id: "mcp-server-1",
        },
      },
    });
  });

  it("refreshes MCP tools with path params", async () => {
    apiClientMock.POST.mockResolvedValueOnce({
      data: [createMcpToolResponse()],
      response: new Response(null, { status: 200 }),
    });

    const { result } = renderHook(() => useRefreshMcpTools(), {
      wrapper: createQueryWrapper(),
    });

    await result.current.mutateAsync({ serverId: "mcp-server-1" });

    expect(hifyApiClient.POST).toHaveBeenCalledWith(
      "/mcp/servers/{server_id}/refresh-tools",
      {
        params: {
          path: {
            server_id: "mcp-server-1",
          },
        },
      },
    );
  });
});

function createQueryWrapper() {
  const queryClient = createHifyQueryClient();

  return function QueryWrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

function createMcpServerResponse() {
  return {
    created_at: "2026-06-23T00:00:00Z",
    description: "Team MCP server",
    endpoint_url: "https://mcp.example.com/mcp",
    id: "mcp-server-1",
    last_discovered_at: "2026-06-23T00:00:00Z",
    name: "Docs MCP",
    status: "active",
    team_id: "team-1",
    transport: "streamable_http",
    updated_at: "2026-06-23T00:00:00Z",
  };
}

function createMcpToolResponse() {
  return {
    created_at: "2026-06-23T00:00:00Z",
    description: "Search docs",
    id: "mcp-tool-1",
    input_schema: { type: "object" },
    last_seen_at: "2026-06-23T00:00:00Z",
    name: "docs.search",
    server_id: "mcp-server-1",
    status: "active",
    team_id: "team-1",
    updated_at: "2026-06-23T00:00:00Z",
  };
}
