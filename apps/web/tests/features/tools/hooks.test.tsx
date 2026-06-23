import { QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useCreateTool, useTool, useTools } from "@/features/tools";
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

describe("tool hooks", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("lists tools", async () => {
    apiClientMock.GET.mockResolvedValueOnce({
      data: [createToolResponse()],
      response: new Response(null, { status: 200 }),
    });

    const { result } = renderHook(() => useTools(), {
      wrapper: createQueryWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(hifyApiClient.GET).toHaveBeenCalledWith("/tools");
    expect(result.current.data?.[0]?.id).toBe("tool-1");
  });

  it("gets tool details with path params", async () => {
    apiClientMock.GET.mockResolvedValueOnce({
      data: createToolResponse(),
      response: new Response(null, { status: 200 }),
    });

    const { result } = renderHook(() => useTool({ toolId: "tool-1" }), {
      wrapper: createQueryWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(hifyApiClient.GET).toHaveBeenCalledWith("/tools/{tool_id}", {
      params: {
        path: {
          tool_id: "tool-1",
        },
      },
    });
  });

  it("creates tools with the backend request contract", async () => {
    apiClientMock.POST.mockResolvedValueOnce({
      data: createToolResponse(),
      response: new Response(null, { status: 201 }),
    });

    const { result } = renderHook(() => useCreateTool(), {
      wrapper: createQueryWrapper(),
    });

    const tool = await result.current.mutateAsync({
      builtin_name: null,
      description: "Search internal docs",
      endpoint_url: "https://tools.example.com/search",
      http_headers: { "X-Team": "platform" },
      http_method: "POST",
      input_schema: { type: "object" },
      mcp_server_id: null,
      mcp_tool_id: null,
      mcp_tool_name: null,
      name: "Search docs",
      tool_kind: "http",
    });

    expect(hifyApiClient.POST).toHaveBeenCalledWith("/tools", {
      body: {
        builtin_name: null,
        description: "Search internal docs",
        endpoint_url: "https://tools.example.com/search",
        http_headers: { "X-Team": "platform" },
        http_method: "POST",
        input_schema: { type: "object" },
        mcp_server_id: null,
        mcp_tool_id: null,
        mcp_tool_name: null,
        name: "Search docs",
        tool_kind: "http",
      },
    });
    expect(tool.id).toBe("tool-1");
  });
});

function createQueryWrapper() {
  const queryClient = createHifyQueryClient();

  return function QueryWrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

function createToolResponse() {
  return {
    builtin_name: null,
    created_at: "2026-06-23T00:00:00Z",
    description: "Search internal docs",
    endpoint_url: "https://tools.example.com/search",
    http_headers: { "X-Team": "platform" },
    http_method: "POST",
    id: "tool-1",
    input_schema: { type: "object" },
    mcp_server_id: null,
    mcp_tool_id: null,
    mcp_tool_name: null,
    name: "Search docs",
    status: "active",
    team_id: "team-1",
    tool_kind: "http",
    updated_at: "2026-06-23T00:00:00Z",
  };
}
