import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ConversationDetail } from "@/features/conversations/components/conversation-detail";

const hookMocks = vi.hoisted(() => ({
  appendMessage: vi.fn(),
  createRun: vi.fn(),
  refetchConversation: vi.fn(),
  refetchMessages: vi.fn(),
  startRunStream: vi.fn(),
}));

vi.mock("@/features/conversations", () => ({
  useAppendConversationMessage: () => ({
    error: null,
    isPending: false,
    mutateAsync: hookMocks.appendMessage,
  }),
  useConversation: () => ({
    data: createConversationResponse(),
    error: null,
    isFetching: false,
    refetch: hookMocks.refetchConversation,
  }),
  useConversationMessages: () => ({
    data: {
      has_more: false,
      items: [createMessageResponse()],
      next_cursor: null,
    },
    error: null,
    isFetching: false,
    refetch: hookMocks.refetchMessages,
  }),
}));

vi.mock("@/features/runs", () => ({
  useCreateRun: () => ({
    error: null,
    isPending: false,
    mutateAsync: hookMocks.createRun,
  }),
  useRunEvents: () => ({
    data: {
      has_more: false,
      items: [],
      next_cursor: null,
    },
    error: null,
    isFetching: false,
    refetch: vi.fn(),
  }),
  useRunStream: () => ({
    error: null,
    isStreaming: false,
    start: hookMocks.startRunStream,
    status: "idle",
    stop: vi.fn(),
  }),
}));

describe("ConversationDetail", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("renders conversation messages and sends new user messages", async () => {
    hookMocks.appendMessage.mockResolvedValueOnce(createMessageResponse({ id: "message-2" }));

    render(<ConversationDetail conversationId="conversation-1" />);

    expect(screen.getByText("Support chat")).toBeTruthy();
    expect(screen.getByText("Hello")).toBeTruthy();

    fireEvent.change(screen.getByLabelText("User message"), {
      target: { value: " Continue " },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));

    await waitFor(() => expect(hookMocks.appendMessage).toHaveBeenCalledTimes(1));
    expect(hookMocks.appendMessage).toHaveBeenCalledWith({
      content: "Continue",
      conversationId: "conversation-1",
      idempotency_key: expect.stringMatching(/^message-/),
    });
  });

  it("starts a streaming run from the conversation detail page", async () => {
    hookMocks.createRun.mockResolvedValueOnce(createRunResponse());
    hookMocks.startRunStream.mockImplementationOnce(({ onEvent }) => {
      onEvent(
        createRunEventResponse({
          event_type: "output.text_delta",
          payload: { text: "Live answer" },
          sequence_number: 2,
        }),
      );

      return Promise.resolve();
    });

    render(<ConversationDetail conversationId="conversation-1" />);

    fireEvent.change(screen.getByLabelText("Idempotency key"), {
      target: { value: "run-key" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Start run" }));

    await waitFor(() => expect(hookMocks.createRun).toHaveBeenCalledTimes(1));
    expect(hookMocks.createRun).toHaveBeenCalledWith({
      conversation_id: "conversation-1",
      idempotency_key: "run-key",
    });
    expect(await screen.findByText("Live answer")).toBeTruthy();
  });
});

function createConversationResponse() {
  return {
    agent_id: "agent-1",
    created_at: "2026-06-23T00:00:00Z",
    id: "conversation-1",
    message_count: 1,
    status: "active",
    team_id: "team-1",
    title: "Support chat",
    updated_at: "2026-06-23T00:00:00Z",
  };
}

function createMessageResponse(override: Record<string, unknown> = {}) {
  return {
    content: "Hello",
    conversation_id: "conversation-1",
    created_at: "2026-06-23T00:00:00Z",
    id: "message-1",
    role: "user",
    sequence_number: 1,
    status: "created",
    team_id: "team-1",
    ...override,
  };
}

function createRunResponse(override: Record<string, unknown> = {}) {
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

function createRunEventResponse(override: Record<string, unknown> = {}) {
  return {
    created_at: "2026-06-23T00:00:00Z",
    event_type: "run.created",
    id: `event-${override.sequence_number ?? 1}`,
    payload: {
      run_id: "run-1",
    },
    run_id: "run-1",
    sequence_number: 1,
    team_id: "team-1",
    ...override,
  };
}
