import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { UsageManagement } from "@/features/usage/components/usage-management";

const hookMocks = vi.hoisted(() => ({
  setQuota: vi.fn(),
}));

vi.mock("@/features/usage/hooks", () => ({
  useSetUsageQuota: () => ({
    data: undefined,
    error: null,
    isPending: false,
    mutateAsync: hookMocks.setQuota,
  }),
  useTeamUsageSummary: () => ({
    data: createUsageSummaryResponse(),
    error: null,
    isLoading: false,
  }),
  useUsageCostByDay: () => ({
    data: createCostByDayResponse(),
    error: null,
    isLoading: false,
  }),
  useUsageCostByModel: () => ({
    data: createCostByModelResponse(),
    error: null,
    isLoading: false,
  }),
  useUsageCostSummary: () => ({
    data: createCostSummaryResponse(),
    error: null,
    isLoading: false,
  }),
  useUsageQuotaStatus: () => ({
    data: createQuotaStatusResponse(),
    error: null,
    isLoading: false,
  }),
}));

describe("UsageManagement", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("renders usage summary, quota status, and cost breakdowns", () => {
    render(<UsageManagement />);

    expect(screen.getByText("Team usage and budget status")).toBeTruthy();
    expect(screen.getByText("gpt-4.1-mini")).toBeTruthy();
    expect(screen.getByText("2026-06-23")).toBeTruthy();
    expect(screen.getAllByText("$0.001000").length).toBeGreaterThan(0);
  });

  it("submits numeric quota changes", async () => {
    hookMocks.setQuota.mockResolvedValueOnce({
      monthly_token_limit: 1000,
      team_id: "team-1",
      version: 2,
    });
    render(<UsageManagement />);

    fireEvent.change(screen.getByLabelText("Monthly token limit"), {
      target: { value: "1000" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save quota" }));

    await waitFor(() =>
      expect(hookMocks.setQuota).toHaveBeenCalledWith({
        monthly_token_limit: 1000,
      }),
    );
  });

  it("submits null quota when the quota field is blank", async () => {
    hookMocks.setQuota.mockResolvedValueOnce({
      monthly_token_limit: null,
      team_id: "team-1",
      version: 3,
    });
    render(<UsageManagement />);

    fireEvent.click(screen.getByRole("button", { name: "Save quota" }));

    await waitFor(() =>
      expect(hookMocks.setQuota).toHaveBeenCalledWith({
        monthly_token_limit: null,
      }),
    );
  });

  it("applies a cost period without calling quota mutation", () => {
    render(<UsageManagement />);

    fireEvent.change(screen.getByLabelText("From date"), {
      target: { value: "2026-06-01" },
    });
    fireEvent.change(screen.getByLabelText("To date"), {
      target: { value: "2026-06-23" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Apply period" }));

    expect(screen.getByText("2026-06-01 to 2026-06-23")).toBeTruthy();
    expect(hookMocks.setQuota).not.toHaveBeenCalled();
  });
});

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
