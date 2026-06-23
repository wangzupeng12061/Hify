import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { McpManagement } from "@/features/mcp/components/mcp-management";

const hookMocks = vi.hoisted(() => ({
  createServer: vi.fn(),
  refreshTools: vi.fn(),
}));

vi.mock("@/features/mcp/hooks", () => ({
  useCreateMcpServer: () => ({
    data: undefined,
    error: null,
    isPending: false,
    mutateAsync: hookMocks.createServer,
  }),
  useMcpServers: () => ({
    data: [createMcpServerResponse()],
    error: null,
    isLoading: false,
  }),
  useMcpTools: () => ({
    data: [createMcpToolResponse()],
    error: null,
    isLoading: false,
  }),
  useRefreshMcpTools: () => ({
    data: undefined,
    error: null,
    isPending: false,
    mutateAsync: hookMocks.refreshTools,
  }),
}));

describe("McpManagement", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("renders servers and discovered tools", () => {
    render(<McpManagement />);

    expect(screen.getAllByText("Docs MCP").length).toBeGreaterThan(0);
    expect(screen.getByText("docs.search")).toBeTruthy();
    expect(screen.getByText("1 loaded")).toBeTruthy();
  });

  it("submits MCP server creation values with cleaned optional fields", async () => {
    hookMocks.createServer.mockResolvedValueOnce(createMcpServerResponse());
    render(<McpManagement />);

    fireEvent.change(screen.getByLabelText("Server name"), {
      target: { value: " Docs MCP " },
    });
    fireEvent.change(screen.getByLabelText("Description"), {
      target: { value: " Team docs server " },
    });
    fireEvent.change(screen.getByLabelText("Endpoint URL"), {
      target: { value: " https://mcp.example.com/mcp " },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create MCP server" }));

    await waitFor(() =>
      expect(hookMocks.createServer).toHaveBeenCalledWith({
        description: "Team docs server",
        endpoint_url: "https://mcp.example.com/mcp",
        name: "Docs MCP",
        transport: "streamable_http",
      }),
    );
  });

  it("refreshes tools for the selected server", async () => {
    hookMocks.refreshTools.mockResolvedValueOnce([createMcpToolResponse()]);
    render(<McpManagement />);

    fireEvent.click(screen.getByRole("button", { name: "Refresh tools" }));

    await waitFor(() =>
      expect(hookMocks.refreshTools).toHaveBeenCalledWith({
        serverId: "mcp-server-1",
      }),
    );
  });
});

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
