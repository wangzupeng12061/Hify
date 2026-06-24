import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { UserChatWorkspace } from "@/features/chat/components/user-chat-workspace";

const hookMocks = vi.hoisted(() => ({
  appendMessage: vi.fn(),
  createConversation: vi.fn(),
  createRun: vi.fn(),
  startRunStream: vi.fn(),
}));

vi.mock("@/features/agents", () => ({
  useAgents: () => ({
    data: [createPublishedAgentResponse(), createDraftAgentResponse()],
    error: null,
    isLoading: false,
  }),
}));

vi.mock("@/features/conversations", () => ({
  useAppendConversationMessage: () => ({
    error: null,
    isPending: false,
    mutateAsync: hookMocks.appendMessage,
  }),
  useConversationMessages: () => ({
    data: {
      has_more: false,
      items: [],
      next_cursor: null,
    },
    error: null,
    isFetching: false,
    refetch: vi.fn(),
  }),
  useCreateConversation: () => ({
    error: null,
    isPending: false,
    mutateAsync: hookMocks.createConversation,
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

describe("UserChatWorkspace", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("shows only published agents as chat candidates", () => {
    render(<UserChatWorkspace />);

    expect(screen.getByText("Support Agent · v1")).toBeTruthy();
    expect(screen.queryByText("Draft Agent · v0")).toBeNull();
    expect(screen.queryByText("Latest run diagnostics")).toBeNull();
  });

  it("creates a conversation, sends a message, and starts a streaming run", async () => {
    hookMocks.createConversation.mockResolvedValueOnce(createConversationResponse());
    hookMocks.appendMessage.mockResolvedValueOnce(createMessageResponse());
    hookMocks.createRun.mockResolvedValueOnce(createRunResponse());
    hookMocks.startRunStream.mockImplementationOnce(({ onEvent }) => {
      onEvent(
        createRunEventResponse({
          event_type: "output.text_delta",
          payload: { text: "Hello from agent" },
          sequence_number: 2,
        }),
      );

      return Promise.resolve();
    });

    render(<UserChatWorkspace />);

    fireEvent.change(screen.getByLabelText("Agent"), {
      target: { value: "agent-1" },
    });
    fireEvent.change(screen.getByLabelText("Title"), {
      target: { value: "Support chat" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Start conversation" }));

    await waitFor(() => expect(hookMocks.createConversation).toHaveBeenCalledTimes(1));
    expect(hookMocks.createConversation).toHaveBeenCalledWith({
      agent_id: "agent-1",
      title: "Support chat",
    });

    fireEvent.change(screen.getByLabelText("Message"), {
      target: { value: " Help me " },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send and run" }));

    await waitFor(() => expect(hookMocks.appendMessage).toHaveBeenCalledTimes(1));
    expect(hookMocks.appendMessage).toHaveBeenCalledWith({
      content: "Help me",
      conversationId: "conversation-1",
      idempotency_key: expect.stringMatching(/^message-/),
    });

    await waitFor(() => expect(hookMocks.createRun).toHaveBeenCalledTimes(1));
    expect(hookMocks.createRun).toHaveBeenCalledWith({
      conversation_id: "conversation-1",
      idempotency_key: expect.stringMatching(/^run-/),
    });
    expect(await screen.findByText("Hello from agent")).toBeTruthy();
  });
});

function createPublishedAgentResponse() {
  return {
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
  };
}

function createDraftAgentResponse() {
  return {
    ...createPublishedAgentResponse(),
    id: "agent-draft-1",
    latest_version_number: 0,
    name: "Draft Agent",
    status: "draft",
  };
}

function createConversationResponse() {
  return {
    agent_id: "agent-1",
    created_at: "2026-06-23T00:00:00Z",
    id: "conversation-1",
    message_count: 0,
    status: "active",
    team_id: "team-1",
    title: "Support chat",
    updated_at: "2026-06-23T00:00:00Z",
  };
}

function createMessageResponse() {
  return {
    content: "Help me",
    conversation_id: "conversation-1",
    created_at: "2026-06-23T00:00:00Z",
    id: "message-1",
    role: "user",
    sequence_number: 1,
    status: "created",
    team_id: "team-1",
  };
}

function createRunResponse() {
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
