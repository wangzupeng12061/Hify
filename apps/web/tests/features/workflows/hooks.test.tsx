import { QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  useCreateWorkflow,
  usePublishWorkflow,
  useUpdateWorkflowDraft,
  useValidateWorkflowDraft,
  useWorkflow,
  useWorkflows,
} from "@/features/workflows";
import { hifyApiClient } from "@/lib/api/client";
import { createHifyQueryClient } from "@/lib/query/query-client";

const apiClientMock = vi.hoisted(() => ({
  GET: vi.fn(),
  POST: vi.fn(),
  PUT: vi.fn(),
}));

vi.mock("@/lib/api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/client")>();

  return {
    ...actual,
    hifyApiClient: apiClientMock,
  };
});

describe("workflow hooks", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("lists workflows", async () => {
    apiClientMock.GET.mockResolvedValueOnce({
      data: [createWorkflowResponse()],
      response: new Response(null, { status: 200 }),
    });

    const { result } = renderHook(() => useWorkflows(), {
      wrapper: createQueryWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(hifyApiClient.GET).toHaveBeenCalledWith("/workflows");
    expect(result.current.data?.[0]?.id).toBe("workflow-1");
  });

  it("gets workflow details with path params", async () => {
    apiClientMock.GET.mockResolvedValueOnce({
      data: createWorkflowResponse(),
      response: new Response(null, { status: 200 }),
    });

    const { result } = renderHook(() => useWorkflow({ workflowId: "workflow-1" }), {
      wrapper: createQueryWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(hifyApiClient.GET).toHaveBeenCalledWith("/workflows/{workflow_id}", {
      params: {
        path: {
          workflow_id: "workflow-1",
        },
      },
    });
  });

  it("creates workflows with the backend request contract", async () => {
    apiClientMock.POST.mockResolvedValueOnce({
      data: createWorkflowResponse(),
      response: new Response(null, { status: 201 }),
    });

    const { result } = renderHook(() => useCreateWorkflow(), {
      wrapper: createQueryWrapper(),
    });

    const workflow = await result.current.mutateAsync({
      description: "Support workflow",
      draft_definition: createWorkflowDefinition(),
      name: "Support Flow",
    });

    expect(hifyApiClient.POST).toHaveBeenCalledWith("/workflows", {
      body: {
        description: "Support workflow",
        draft_definition: createWorkflowDefinition(),
        name: "Support Flow",
      },
    });
    expect(workflow.id).toBe("workflow-1");
  });

  it("updates workflow drafts with path params", async () => {
    apiClientMock.PUT.mockResolvedValueOnce({
      data: createWorkflowResponse(),
      response: new Response(null, { status: 200 }),
    });

    const { result } = renderHook(() => useUpdateWorkflowDraft(), {
      wrapper: createQueryWrapper(),
    });

    await result.current.mutateAsync({
      draft_definition: createWorkflowDefinition(),
      workflowId: "workflow-1",
    });

    expect(hifyApiClient.PUT).toHaveBeenCalledWith("/workflows/{workflow_id}/draft", {
      body: {
        draft_definition: createWorkflowDefinition(),
      },
      params: {
        path: {
          workflow_id: "workflow-1",
        },
      },
    });
  });

  it("validates and publishes workflows with path params", async () => {
    apiClientMock.POST.mockResolvedValueOnce({
      data: { is_valid: true, issues: [] },
      response: new Response(null, { status: 200 }),
    });
    apiClientMock.POST.mockResolvedValueOnce({
      data: createWorkflowVersionResponse(),
      response: new Response(null, { status: 201 }),
    });

    const wrapper = createQueryWrapper();
    const validationResult = renderHook(() => useValidateWorkflowDraft(), { wrapper });
    const publishResult = renderHook(() => usePublishWorkflow(), { wrapper });

    await validationResult.result.current.mutateAsync({ workflowId: "workflow-1" });
    await publishResult.result.current.mutateAsync({ workflowId: "workflow-1" });

    expect(hifyApiClient.POST).toHaveBeenNthCalledWith(1, "/workflows/{workflow_id}/validate", {
      params: {
        path: {
          workflow_id: "workflow-1",
        },
      },
    });
    expect(hifyApiClient.POST).toHaveBeenNthCalledWith(2, "/workflows/{workflow_id}/publish", {
      params: {
        path: {
          workflow_id: "workflow-1",
        },
      },
    });
  });
});

function createQueryWrapper() {
  const queryClient = createHifyQueryClient();

  return function QueryWrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

function createWorkflowDefinition() {
  return {
    edges: [{ source_node_id: "start", target_node_id: "end" }],
    nodes: [
      { config: {}, id: "start", kind: "start" },
      { config: {}, id: "end", kind: "end" },
    ],
  };
}

function createWorkflowResponse() {
  return {
    created_at: "2026-06-23T00:00:00Z",
    description: "Support workflow",
    draft_definition: createWorkflowDefinition(),
    id: "workflow-1",
    latest_version_number: 0,
    name: "Support Flow",
    status: "draft",
    team_id: "team-1",
    updated_at: "2026-06-23T00:00:00Z",
  };
}

function createWorkflowVersionResponse() {
  return {
    created_at: "2026-06-23T00:00:00Z",
    definition: createWorkflowDefinition(),
    description: "Support workflow",
    id: "workflow-version-1",
    name: "Support Flow",
    team_id: "team-1",
    version_number: 1,
    workflow_id: "workflow-1",
  };
}
