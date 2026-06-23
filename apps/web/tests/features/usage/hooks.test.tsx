import { QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  useSetUsageQuota,
  useTeamUsageSummary,
  useUsageCostByDay,
  useUsageCostByModel,
  useUsageCostSummary,
  useUsageQuotaStatus,
} from "@/features/usage";
import { hifyApiClient } from "@/lib/api/client";
import { createHifyQueryClient } from "@/lib/query/query-client";

const apiClientMock = vi.hoisted(() => ({
  GET: vi.fn(),
  PUT: vi.fn(),
}));

vi.mock("@/lib/api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/client")>();

  return {
    ...actual,
    hifyApiClient: apiClientMock,
  };
});

describe("usage hooks", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("gets team usage summary", async () => {
    apiClientMock.GET.mockResolvedValueOnce({
      data: createUsageSummaryResponse(),
      response: new Response(null, { status: 200 }),
    });

    const { result } = renderHook(() => useTeamUsageSummary(), {
      wrapper: createQueryWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(hifyApiClient.GET).toHaveBeenCalledWith("/usage/summary");
    expect(result.current.data?.total_tokens).toBe(300);
  });

  it("gets quota status", async () => {
    apiClientMock.GET.mockResolvedValueOnce({
      data: createQuotaStatusResponse(),
      response: new Response(null, { status: 200 }),
    });

    const { result } = renderHook(() => useUsageQuotaStatus(), {
      wrapper: createQueryWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(hifyApiClient.GET).toHaveBeenCalledWith("/usage/quota");
  });

  it("gets cost summary with period query params", async () => {
    apiClientMock.GET.mockResolvedValueOnce({
      data: createCostSummaryResponse(),
      response: new Response(null, { status: 200 }),
    });

    const { result } = renderHook(
      () =>
        useUsageCostSummary({
          from: "2026-06-01T00:00:00.000Z",
          to: "2026-06-23T00:00:00.000Z",
        }),
      { wrapper: createQueryWrapper() },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(hifyApiClient.GET).toHaveBeenCalledWith("/usage/cost-summary", {
      params: {
        query: {
          from: "2026-06-01T00:00:00.000Z",
          to: "2026-06-23T00:00:00.000Z",
        },
      },
    });
  });

  it("gets model and day cost breakdowns", async () => {
    apiClientMock.GET.mockResolvedValueOnce({
      data: createCostByModelResponse(),
      response: new Response(null, { status: 200 }),
    });
    apiClientMock.GET.mockResolvedValueOnce({
      data: createCostByDayResponse(),
      response: new Response(null, { status: 200 }),
    });

    const modelResult = renderHook(() => useUsageCostByModel(), {
      wrapper: createQueryWrapper(),
    });
    const dayResult = renderHook(() => useUsageCostByDay(), {
      wrapper: createQueryWrapper(),
    });

    await waitFor(() => expect(modelResult.result.current.isSuccess).toBe(true));
    await waitFor(() => expect(dayResult.result.current.isSuccess).toBe(true));

    expect(hifyApiClient.GET).toHaveBeenNthCalledWith(1, "/usage/cost-by-model", {
      params: {
        query: {
          from: null,
          to: null,
        },
      },
    });
    expect(hifyApiClient.GET).toHaveBeenNthCalledWith(2, "/usage/cost-by-day", {
      params: {
        query: {
          from: null,
          to: null,
        },
      },
    });
  });

  it("sets usage quota with request body", async () => {
    apiClientMock.PUT.mockResolvedValueOnce({
      data: {
        monthly_token_limit: 1000,
        team_id: "team-1",
        version: 2,
      },
      response: new Response(null, { status: 200 }),
    });

    const { result } = renderHook(() => useSetUsageQuota(), {
      wrapper: createQueryWrapper(),
    });

    await result.current.mutateAsync({
      monthly_token_limit: 1000,
    });

    expect(hifyApiClient.PUT).toHaveBeenCalledWith("/usage/quota", {
      body: {
        monthly_token_limit: 1000,
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

function createUsageSummaryResponse() {
  return {
    cost_amount: "0.001000",
    input_tokens: 100,
    output_tokens: 200,
    run_id: null,
    team_id: "team-1",
    total_tokens: 300,
  };
}

function createQuotaStatusResponse() {
  return {
    is_exceeded: false,
    monthly_token_limit: 1000,
    period_end: "2026-07-01T00:00:00Z",
    period_start: "2026-06-01T00:00:00Z",
    remaining_tokens: 700,
    team_id: "team-1",
    used_tokens: 300,
  };
}

function createCostSummaryResponse() {
  return {
    cost_amount: "0.001000",
    input_tokens: 100,
    is_quota_exceeded: false,
    monthly_token_limit: 1000,
    output_tokens: 200,
    period_end: "2026-06-23T00:00:00Z",
    period_start: "2026-06-01T00:00:00Z",
    remaining_tokens: 700,
    team_id: "team-1",
    total_tokens: 300,
  };
}

function createCostByModelResponse() {
  return {
    items: [
      {
        cost_amount: "0.001000",
        input_tokens: 100,
        model: "gpt-4.1-mini",
        output_tokens: 200,
        provider: "openai",
        provider_model_id: "model-1",
        total_tokens: 300,
      },
    ],
    period_end: "2026-06-23T00:00:00Z",
    period_start: "2026-06-01T00:00:00Z",
    team_id: "team-1",
  };
}

function createCostByDayResponse() {
  return {
    items: [
      {
        cost_amount: "0.001000",
        input_tokens: 100,
        output_tokens: 200,
        total_tokens: 300,
        usage_date: "2026-06-23",
      },
    ],
    period_end: "2026-06-23T00:00:00Z",
    period_start: "2026-06-01T00:00:00Z",
    team_id: "team-1",
  };
}
