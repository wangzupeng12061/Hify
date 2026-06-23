import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ConversationsHistory } from "@/features/conversations/components/conversations-history";

const hookMocks = vi.hoisted(() => ({
  useConversations: vi.fn(),
}));

vi.mock("@/features/conversations", () => ({
  useConversations: hookMocks.useConversations,
}));

describe("ConversationsHistory", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("renders recent conversations with detail links", () => {
    hookMocks.useConversations.mockReturnValue({
      data: {
        has_more: false,
        items: [createConversationResponse()],
        next_cursor: null,
      },
      error: null,
      isFetching: false,
    });

    render(<ConversationsHistory />);

    expect(screen.getByText("Support chat")).toBeTruthy();
    expect(screen.getByText(/2 messages/)).toBeTruthy();
    expect(screen.getByRole("link", { name: "Open" }).getAttribute("href")).toBe(
      "/conversations/conversation-1",
    );
  });
});

function createConversationResponse() {
  return {
    agent_id: "agent-1",
    created_at: "2026-06-23T00:00:00Z",
    id: "conversation-1",
    message_count: 2,
    status: "active",
    team_id: "team-1",
    title: "Support chat",
    updated_at: "2026-06-23T00:00:00Z",
  };
}
