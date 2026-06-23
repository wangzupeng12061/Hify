import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AgentsManagement } from "@/features/agents/components/agents-management";

const hookMocks = vi.hoisted(() => ({
  createAgent: vi.fn(),
  publishAgent: vi.fn(),
}));

vi.mock("@/features/agents/hooks", () => ({
  useCreateAgent: () => ({
    data: undefined,
    error: null,
    isPending: false,
    mutateAsync: hookMocks.createAgent,
  }),
  usePublishAgent: () => ({
    data: undefined,
    error: null,
    isPending: false,
    mutateAsync: hookMocks.publishAgent,
  }),
}));

vi.mock("@/features/knowledge", () => ({
  useKnowledgeBases: () => ({
    data: [createKnowledgeBaseResponse()],
    error: null,
    isLoading: false,
  }),
}));

vi.mock("@/features/providers", () => ({
  useProviderModels: () => ({
    data: [createModelResponse()],
    error: null,
    isLoading: false,
  }),
}));

vi.mock("@/features/workflows", () => ({
  useWorkflows: () => ({
    data: [createWorkflowResponse(), createDraftWorkflowResponse()],
    error: null,
    isLoading: false,
  }),
}));

describe("AgentsManagement", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("submits agent creation values with cleaned optional fields", async () => {
    hookMocks.createAgent.mockResolvedValueOnce(createAgentResponse());
    render(<AgentsManagement />);

    fireEvent.change(screen.getByLabelText("Agent name"), {
      target: { value: "Support Agent" },
    });
    fireEvent.change(screen.getByLabelText("Description"), {
      target: { value: " Support assistant " },
    });
    fireEvent.change(screen.getByLabelText("Provider model"), {
      target: { value: "model-1" },
    });
    fireEvent.click(screen.getByLabelText("Team Docs"));
    fireEvent.change(screen.getByLabelText("Workflow"), {
      target: { value: "workflow-1" },
    });
    fireEvent.change(screen.getByLabelText("System prompt"), {
      target: { value: " Help the team. " },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create agent" }));

    await waitFor(() =>
      expect(hookMocks.createAgent).toHaveBeenCalledWith({
        description: "Support assistant",
        knowledge_base_ids: ["kb-1"],
        name: "Support Agent",
        provider_model_id: "model-1",
        system_prompt: "Help the team.",
        workflow_id: "workflow-1",
      }),
    );
  });

  it("submits agent publishing values", async () => {
    hookMocks.publishAgent.mockResolvedValueOnce({});
    render(<AgentsManagement />);

    fireEvent.change(screen.getByLabelText("Agent ID"), {
      target: { value: "agent-1" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Publish agent" }));

    await waitFor(() =>
      expect(hookMocks.publishAgent).toHaveBeenCalledWith({
        agentId: "agent-1",
      }),
    );
  });

  it("shows only published workflows as binding candidates", () => {
    render(<AgentsManagement />);

    expect(screen.getByText("Escalation Workflow · v2")).toBeTruthy();
    expect(screen.queryByText("Draft Workflow · v0")).toBeNull();
  });
});

function createWorkflowResponse() {
  return {
    created_at: "2026-06-23T00:00:00Z",
    description: "Published workflow",
    draft_definition: {
      edges: [{ source_node_id: "start", target_node_id: "end" }],
      nodes: [
        { config: {}, id: "start", kind: "start" },
        { config: {}, id: "end", kind: "end" },
      ],
    },
    id: "workflow-1",
    latest_version_number: 2,
    name: "Escalation Workflow",
    status: "published",
    team_id: "team-1",
    updated_at: "2026-06-23T00:00:00Z",
  };
}

function createAgentResponse() {
  return {
    created_at: "2026-06-23T00:00:00Z",
    description: "Support assistant",
    id: "agent-1",
    knowledge_base_ids: ["kb-1"],
    latest_version_number: 0,
    name: "Support Agent",
    provider_model_id: "model-1",
    status: "draft",
    team_id: "team-1",
    updated_at: "2026-06-23T00:00:00Z",
    workflow_id: "workflow-1",
  };
}

function createKnowledgeBaseResponse() {
  return {
    chunk_count: 3,
    created_at: "2026-06-23T00:00:00Z",
    description: "Team documents",
    document_count: 1,
    embedding_dimensions: 1536,
    embedding_model_id: "embedding-model-1",
    id: "kb-1",
    name: "Team Docs",
    status: "active",
    team_id: "team-1",
    updated_at: "2026-06-23T00:00:00Z",
  };
}

function createModelResponse() {
  return {
    context_window_tokens: 128000,
    display_name: "GPT-4.1",
    id: "model-1",
    kind: "chat",
    model_name: "gpt-4.1",
    price_per_1m_input_tokens: null,
    price_per_1m_output_tokens: null,
    provider_id: "provider-1",
    provider_name: "OpenAI",
    provider_type: "openai",
    status: "active",
    supports_structured_output: true,
    supports_tools: true,
    supports_vision: false,
    team_id: "team-1",
  };
}

function createDraftWorkflowResponse() {
  return {
    ...createWorkflowResponse(),
    id: "workflow-draft-1",
    latest_version_number: 0,
    name: "Draft Workflow",
    status: "draft",
  };
}
