import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { SettingsDialog } from "@/features/settings";

vi.mock("@/features/agents", () => ({
  useAgents: () => ({
    data: [
      {
        created_at: "2026-06-23T00:00:00Z",
        description: "Published support assistant",
        id: "agent-1",
        knowledge_base_ids: [],
        latest_version_number: 1,
        name: "Support Agent",
        provider_model_id: "model-1",
        status: "published",
        team_id: "team-1",
        updated_at: "2026-06-23T00:00:00Z",
        workflow_id: null,
      },
    ],
    error: null,
    isLoading: false,
  }),
}));

describe("SettingsDialog", () => {
  afterEach(() => {
    cleanup();
    window.localStorage.clear();
    vi.clearAllMocks();
  });

  it("stores chat preferences in local storage", () => {
    render(<SettingsDialog isOpen={true} onClose={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: "Chat" }));
    fireEvent.change(screen.getByLabelText("默认 Agent"), {
      target: { value: "agent-1" },
    });
    fireEvent.click(screen.getByLabelText("显示工具调用过程"));

    expect(readStoredSettings()).toMatchObject({
      defaultAgentId: "agent-1",
      showToolActivity: false,
    });
  });
});

function readStoredSettings(): Record<string, unknown> {
  const rawSettings = window.localStorage.getItem("hify.localSettings");
  expect(rawSettings).not.toBeNull();
  return JSON.parse(rawSettings ?? "{}") as Record<string, unknown>;
}
