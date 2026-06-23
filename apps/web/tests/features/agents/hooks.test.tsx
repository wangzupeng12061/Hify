import { QueryClientProvider } from "@tanstack/react-query";
import { renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useCreateAgent, usePublishAgent } from "@/features/agents";
import type { Agent, AgentVersion } from "@/features/agents";
import { hifyApiClient } from "@/lib/api/client";
import { createHifyQueryClient } from "@/lib/query/query-client";

const apiClientMock = vi.hoisted(() => ({
  POST: vi.fn(),
}));

vi.mock("@/lib/api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/client")>();

  return {
    ...actual,
    hifyApiClient: apiClientMock,
  };
});

describe("agent hooks", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("creates agents with the backend request contract", async () => {
    apiClientMock.POST.mockResolvedValueOnce({
      data: createAgentResponse(),
      response: new Response(null, { status: 201 }),
    });

    const { result } = renderHook(() => useCreateAgent(), {
      wrapper: createQueryWrapper(),
    });

    const agent = await result.current.mutateAsync({
      description: "Support assistant",
      knowledge_base_ids: ["kb-1", "kb-2"],
      name: "Support Agent",
      provider_model_id: "model-1",
      system_prompt: "Help the team.",
      workflow_id: null,
    });

    expect(hifyApiClient.POST).toHaveBeenCalledWith("/agents", {
      body: {
        description: "Support assistant",
        knowledge_base_ids: ["kb-1", "kb-2"],
        name: "Support Agent",
        provider_model_id: "model-1",
        system_prompt: "Help the team.",
        workflow_id: null,
      },
    });
    expect(agent.id).toBe("agent-1");
  });

  it("publishes agents with path params", async () => {
    apiClientMock.POST.mockResolvedValueOnce({
      data: createAgentVersionResponse(),
      response: new Response(null, { status: 201 }),
    });

    const { result } = renderHook(() => usePublishAgent(), {
      wrapper: createQueryWrapper(),
    });

    const version = await result.current.mutateAsync({ agentId: "agent-1" });

    expect(hifyApiClient.POST).toHaveBeenCalledWith("/agents/{agent_id}/publish", {
      params: {
        path: {
          agent_id: "agent-1",
        },
      },
    });
    expect(version.version_number).toBe(1);
  });
});

function createQueryWrapper() {
  const queryClient = createHifyQueryClient();

  return function QueryWrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

function createAgentResponse(override: Partial<Agent> = {}): Agent {
  return {
    created_at: "2026-06-23T00:00:00Z",
    description: "Support assistant",
    id: "agent-1",
    knowledge_base_ids: ["kb-1", "kb-2"],
    latest_version_number: 0,
    name: "Support Agent",
    provider_model_id: "model-1",
    status: "draft",
    team_id: "team-1",
    updated_at: "2026-06-23T00:00:00Z",
    workflow_id: null,
    ...override,
  };
}

function createAgentVersionResponse(override: Partial<AgentVersion> = {}): AgentVersion {
  return {
    agent_id: "agent-1",
    context_window_tokens: 128000,
    created_at: "2026-06-23T00:00:00Z",
    description: "Support assistant",
    id: "agent-version-1",
    knowledge_base_ids: ["kb-1", "kb-2"],
    model_display_name: "GPT-4.1",
    model_name: "gpt-4.1",
    name: "Support Agent",
    provider_model_id: "model-1",
    provider_name: "OpenAI",
    provider_type: "openai",
    supports_structured_output: true,
    supports_tools: true,
    supports_vision: false,
    system_prompt: "Help the team.",
    team_id: "team-1",
    version_number: 1,
    workflow_definition: null,
    workflow_id: null,
    workflow_name: null,
    workflow_version_id: null,
    workflow_version_number: null,
    ...override,
  };
}
