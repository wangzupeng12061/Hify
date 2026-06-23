import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ToolsManagement } from "@/features/tools/components/tools-management";

const hookMocks = vi.hoisted(() => ({
  createTool: vi.fn(),
}));

vi.mock("@/features/tools/hooks", () => ({
  useCreateTool: () => ({
    data: undefined,
    error: null,
    isPending: false,
    mutateAsync: hookMocks.createTool,
  }),
  useTools: () => ({
    data: [createHttpToolResponse(), createBuiltinToolResponse(), createMcpToolResponse()],
    error: null,
    isLoading: false,
  }),
}));

describe("ToolsManagement", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("renders tool catalog entries and counts", () => {
    render(<ToolsManagement />);

    expect(screen.getByText("Search docs")).toBeTruthy();
    expect(screen.getByText("Web search")).toBeTruthy();
    expect(screen.getByText("MCP calculator")).toBeTruthy();
    expect(screen.getByText("3 loaded")).toBeTruthy();
  });

  it("submits HTTP tool creation values with parsed JSON fields", async () => {
    hookMocks.createTool.mockResolvedValueOnce(createHttpToolResponse());
    render(<ToolsManagement />);

    const httpForm = screen.getByRole("button", { name: "Create HTTP tool" }).closest("form");
    if (httpForm === null) {
      throw new Error("HTTP tool form was not rendered.");
    }

    fireEvent.change(within(httpForm).getByLabelText("Tool name"), {
      target: { value: " Search Docs " },
    });
    fireEvent.change(within(httpForm).getByLabelText("Description"), {
      target: { value: " Internal search " },
    });
    fireEvent.change(within(httpForm).getByLabelText("Endpoint URL"), {
      target: { value: " https://tools.example.com/search " },
    });
    fireEvent.change(within(httpForm).getByLabelText("HTTP method"), {
      target: { value: "POST" },
    });
    fireEvent.change(within(httpForm).getByLabelText("HTTP headers JSON"), {
      target: { value: '{ "X-Team": "platform" }' },
    });
    fireEvent.change(within(httpForm).getByLabelText("Input schema JSON"), {
      target: { value: '{ "type": "object" }' },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create HTTP tool" }));

    await waitFor(() =>
      expect(hookMocks.createTool).toHaveBeenCalledWith({
        builtin_name: null,
        description: "Internal search",
        endpoint_url: "https://tools.example.com/search",
        http_headers: { "X-Team": "platform" },
        http_method: "POST",
        input_schema: { type: "object" },
        mcp_server_id: null,
        mcp_tool_id: null,
        mcp_tool_name: null,
        name: "Search Docs",
        tool_kind: "http",
      }),
    );
  });

  it("submits builtin tool creation values", async () => {
    hookMocks.createTool.mockResolvedValueOnce(createBuiltinToolResponse());
    render(<ToolsManagement />);

    const builtinForm = screen.getByRole("button", { name: "Create builtin tool" }).closest("form");
    if (builtinForm === null) {
      throw new Error("Builtin tool form was not rendered.");
    }

    fireEvent.change(within(builtinForm).getByLabelText("Tool name"), {
      target: { value: " Web Search " },
    });
    fireEvent.change(within(builtinForm).getByLabelText("Description"), {
      target: { value: " Search the web " },
    });
    fireEvent.change(within(builtinForm).getByLabelText("Builtin name"), {
      target: { value: " web.search " },
    });
    fireEvent.change(within(builtinForm).getByLabelText("Input schema JSON"), {
      target: { value: '{ "type": "object" }' },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create builtin tool" }));

    await waitFor(() =>
      expect(hookMocks.createTool).toHaveBeenCalledWith({
        builtin_name: "web.search",
        description: "Search the web",
        endpoint_url: null,
        http_headers: {},
        http_method: null,
        input_schema: { type: "object" },
        mcp_server_id: null,
        mcp_tool_id: null,
        mcp_tool_name: null,
        name: "Web Search",
        tool_kind: "builtin",
      }),
    );
  });

  it("shows a form error when JSON fields are invalid", async () => {
    render(<ToolsManagement />);

    const httpForm = screen.getByRole("button", { name: "Create HTTP tool" }).closest("form");
    if (httpForm === null) {
      throw new Error("HTTP tool form was not rendered.");
    }

    fireEvent.change(within(httpForm).getByLabelText("Tool name"), {
      target: { value: "Search Docs" },
    });
    fireEvent.change(within(httpForm).getByLabelText("Endpoint URL"), {
      target: { value: "https://tools.example.com/search" },
    });
    fireEvent.change(within(httpForm).getByLabelText("HTTP headers JSON"), {
      target: { value: "{ invalid json" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create HTTP tool" }));

    await waitFor(() => expect(screen.getByRole("alert")).toBeTruthy());
    expect(screen.getByText("HTTP headers must be valid JSON.")).toBeTruthy();
    expect(hookMocks.createTool).not.toHaveBeenCalled();
  });
});

function createHttpToolResponse() {
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

function createBuiltinToolResponse() {
  return {
    builtin_name: "web.search",
    created_at: "2026-06-23T00:00:00Z",
    description: "Search the web",
    endpoint_url: null,
    http_headers: {},
    http_method: null,
    id: "tool-2",
    input_schema: { type: "object" },
    mcp_server_id: null,
    mcp_tool_id: null,
    mcp_tool_name: null,
    name: "Web search",
    status: "active",
    team_id: "team-1",
    tool_kind: "builtin",
    updated_at: "2026-06-23T00:00:00Z",
  };
}

function createMcpToolResponse() {
  return {
    builtin_name: null,
    created_at: "2026-06-23T00:00:00Z",
    description: "Calculator from MCP",
    endpoint_url: null,
    http_headers: {},
    http_method: null,
    id: "tool-3",
    input_schema: { type: "object" },
    mcp_server_id: "mcp-server-1",
    mcp_tool_id: "mcp-tool-1",
    mcp_tool_name: "calculator.add",
    name: "MCP calculator",
    status: "active",
    team_id: "team-1",
    tool_kind: "mcp",
    updated_at: "2026-06-23T00:00:00Z",
  };
}
