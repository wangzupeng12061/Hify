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

describe("AgentsManagement", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("submits agent creation values with cleaned optional fields", async () => {
    hookMocks.createAgent.mockResolvedValueOnce({});
    render(<AgentsManagement />);

    fireEvent.change(screen.getByLabelText("Agent name"), {
      target: { value: "Support Agent" },
    });
    fireEvent.change(screen.getByLabelText("Description"), {
      target: { value: " Support assistant " },
    });
    fireEvent.change(screen.getByLabelText("Provider model ID"), {
      target: { value: "model-1" },
    });
    fireEvent.change(screen.getByLabelText("Knowledge base IDs"), {
      target: { value: "kb-1, kb-2, " },
    });
    fireEvent.change(screen.getByLabelText("System prompt"), {
      target: { value: " Help the team. " },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create agent" }));

    await waitFor(() =>
      expect(hookMocks.createAgent).toHaveBeenCalledWith({
        description: "Support assistant",
        knowledge_base_ids: ["kb-1", "kb-2"],
        name: "Support Agent",
        provider_model_id: "model-1",
        system_prompt: "Help the team.",
        workflow_id: null,
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
});
