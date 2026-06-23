import { QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useCancelRun, useCreateRun, useRun, useRunDiagnostics, useRunEvents } from "@/features/runs";
import type { Run, RunDiagnostics, RunEvent } from "@/features/runs";
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

describe("run hooks", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("creates runs with the backend request contract", async () => {
    apiClientMock.POST.mockResolvedValueOnce({
      data: createRunResponse(),
      response: new Response(null, { status: 201 }),
    });

    const { result } = renderHook(() => useCreateRun(), {
      wrapper: createQueryWrapper(),
    });

    const run = await result.current.mutateAsync({
      conversation_id: "conversation-1",
      idempotency_key: "run-key",
    });

    expect(hifyApiClient.POST).toHaveBeenCalledWith("/runs", {
      body: {
        conversation_id: "conversation-1",
        idempotency_key: "run-key",
      },
    });
    expect(run.id).toBe("run-1");
  });

  it("gets runs with path params", async () => {
    apiClientMock.GET.mockResolvedValueOnce({
      data: createRunResponse(),
      response: new Response(null, { status: 200 }),
    });

    const { result } = renderHook(() => useRun({ runId: "run-1" }), {
      wrapper: createQueryWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(hifyApiClient.GET).toHaveBeenCalledWith("/runs/{run_id}", {
      params: {
        path: {
          run_id: "run-1",
        },
      },
    });
  });

  it("lists run events with path and query params", async () => {
    apiClientMock.GET.mockResolvedValueOnce({
      data: {
        has_more: false,
        items: [createRunEventResponse()],
        next_cursor: null,
      },
      response: new Response(null, { status: 200 }),
    });

    const { result } = renderHook(
      () => useRunEvents({ cursor: "cursor-1", limit: 10, runId: "run-1" }),
      { wrapper: createQueryWrapper() },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(hifyApiClient.GET).toHaveBeenCalledWith("/runs/{run_id}/events", {
      params: {
        path: {
          run_id: "run-1",
        },
        query: {
          cursor: "cursor-1",
          limit: 10,
        },
      },
    });
  });

  it("gets run diagnostics with path params", async () => {
    apiClientMock.GET.mockResolvedValueOnce({
      data: createRunDiagnosticsResponse(),
      response: new Response(null, { status: 200 }),
    });

    const { result } = renderHook(() => useRunDiagnostics({ runId: "run-1" }), {
      wrapper: createQueryWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(hifyApiClient.GET).toHaveBeenCalledWith("/runs/{run_id}/diagnostics", {
      params: {
        path: {
          run_id: "run-1",
        },
      },
    });
    expect(result.current.data?.steps[0]?.name).toBe("Workflow LLM node");
  });

  it("cancels runs with path params", async () => {
    apiClientMock.POST.mockResolvedValueOnce({
      data: createRunResponse({ status: "cancelled" }),
      response: new Response(null, { status: 200 }),
    });

    const { result } = renderHook(() => useCancelRun(), {
      wrapper: createQueryWrapper(),
    });

    const run = await result.current.mutateAsync({ runId: "run-1" });

    expect(hifyApiClient.POST).toHaveBeenCalledWith("/runs/{run_id}/cancel", {
      params: {
        path: {
          run_id: "run-1",
        },
      },
    });
    expect(run.status).toBe("cancelled");
  });
});

function createQueryWrapper() {
  const queryClient = createHifyQueryClient();

  return function QueryWrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

function createRunResponse(override: Partial<Run> = {}): Run {
  return {
    agent_id: "agent-1",
    agent_version_id: "agent-version-1",
    completed_at: null,
    conversation_id: "conversation-1",
    created_at: "2026-06-23T00:00:00Z",
    duration_ms: null,
    error_code: null,
    error_message: null,
    event_count: 0,
    id: "run-1",
    started_at: null,
    status: "queued",
    step_count: 0,
    team_id: "team-1",
    updated_at: "2026-06-23T00:00:00Z",
    ...override,
  };
}

function createRunEventResponse(override: Partial<RunEvent> = {}): RunEvent {
  return {
    created_at: "2026-06-23T00:00:00Z",
    event_type: "run.created",
    id: "event-1",
    payload: {
      run_id: "run-1",
    },
    run_id: "run-1",
    sequence_number: 1,
    team_id: "team-1",
    ...override,
  };
}

function createRunDiagnosticsResponse(
  override: Partial<RunDiagnostics> = {},
): RunDiagnostics {
  return {
    agent_id: "agent-1",
    agent_version_id: "agent-version-1",
    completed_at: null,
    conversation_id: "conversation-1",
    created_at: "2026-06-23T00:00:00Z",
    duration_ms: null,
    error_code: null,
    error_message: null,
    event_count: 2,
    id: "run-1",
    started_at: "2026-06-23T00:00:00Z",
    status: "running",
    step_count: 1,
    steps: [
      {
        completed_at: "2026-06-23T00:00:01Z",
        duration_ms: 1000,
        error_code: null,
        error_message: null,
        id: "step-1",
        name: "Workflow LLM node",
        sequence_number: 1,
        started_at: "2026-06-23T00:00:00Z",
        status: "succeeded",
        step_type: "llm_call",
      },
    ],
    team_id: "team-1",
    usage_cost_amount: "0",
    usage_input_tokens: 0,
    usage_output_tokens: 0,
    usage_total_tokens: 0,
    ...override,
  };
}
