import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ChatRunsWorkspace } from "@/features/runs/components/chat-runs-workspace";

const hookMocks = vi.hoisted(() => ({
  appendMessage: vi.fn(),
  cancelRun: vi.fn(),
  createConversation: vi.fn(),
  createRun: vi.fn(),
  refetchRun: vi.fn(),
  refetchRunEvents: vi.fn(),
  startRunStream: vi.fn(),
  stopRunStream: vi.fn(),
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
  }),
  useCreateConversation: () => ({
    error: null,
    isPending: false,
    mutateAsync: hookMocks.createConversation,
  }),
}));

vi.mock("@/features/runs", () => ({
  useCancelRun: () => ({
    error: null,
    isPending: false,
    mutateAsync: hookMocks.cancelRun,
  }),
  useCreateRun: () => ({
    error: null,
    isPending: false,
    mutateAsync: hookMocks.createRun,
  }),
  useRun: () => ({
    data: null,
    error: null,
    isFetching: false,
    refetch: hookMocks.refetchRun,
  }),
  useRunEvents: () => ({
    data: {
      has_more: false,
      items: [],
      next_cursor: null,
    },
    error: null,
    isFetching: false,
    refetch: hookMocks.refetchRunEvents,
  }),
  useRunStream: () => ({
    error: null,
    isStreaming: false,
    start: hookMocks.startRunStream,
    status: "idle",
    stop: hookMocks.stopRunStream,
  }),
}));

describe("ChatRunsWorkspace", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("creates conversations with agent and title input", async () => {
    hookMocks.createConversation.mockResolvedValueOnce(createConversationResponse());

    render(<ChatRunsWorkspace />);

    fireEvent.change(screen.getByLabelText("Agent ID"), {
      target: { value: "agent-1" },
    });
    fireEvent.change(screen.getByLabelText("Title"), {
      target: { value: "Support chat" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create conversation" }));

    await waitFor(() => expect(hookMocks.createConversation).toHaveBeenCalledTimes(1));

    expect(hookMocks.createConversation).toHaveBeenCalledWith({
      agent_id: "agent-1",
      title: "Support chat",
    });
    await waitFor(() => expect(screen.getAllByText("conversation-1").length).toBeGreaterThan(0));
  });

  it("sends a user message after a conversation exists", async () => {
    hookMocks.createConversation.mockResolvedValueOnce(createConversationResponse());
    hookMocks.appendMessage.mockResolvedValueOnce(createMessageResponse());

    render(<ChatRunsWorkspace />);
    await createConversation();

    fireEvent.change(screen.getByLabelText("User message"), {
      target: { value: " Hello team " },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));

    await waitFor(() => expect(hookMocks.appendMessage).toHaveBeenCalledTimes(1));

    expect(hookMocks.appendMessage).toHaveBeenCalledWith({
      content: "Hello team",
      conversationId: "conversation-1",
      idempotency_key: expect.stringMatching(/^message-/),
    });
  });

  it("starts and cancels a run for the current conversation", async () => {
    hookMocks.createConversation.mockResolvedValueOnce(createConversationResponse());
    hookMocks.createRun.mockResolvedValueOnce(createRunResponse());
    hookMocks.cancelRun.mockResolvedValueOnce(createRunResponse({ status: "cancelled" }));

    render(<ChatRunsWorkspace />);
    await createConversation();

    fireEvent.change(screen.getByLabelText("Idempotency key"), {
      target: { value: "run-key" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Start run" }));

    await waitFor(() => expect(hookMocks.createRun).toHaveBeenCalledTimes(1));

    expect(hookMocks.createRun).toHaveBeenCalledWith({
      conversation_id: "conversation-1",
      idempotency_key: "run-key",
    });
    expect(hookMocks.startRunStream).toHaveBeenCalledWith({
      onEvent: expect.any(Function),
      runId: "run-1",
    });

    fireEvent.click(screen.getByRole("button", { name: "Cancel run" }));

    await waitFor(() => expect(hookMocks.cancelRun).toHaveBeenCalledTimes(1));
    expect(hookMocks.cancelRun).toHaveBeenCalledWith({ runId: "run-1" });
    expect(hookMocks.stopRunStream).toHaveBeenCalled();
  });

  it("renders streamed assistant output after starting a run", async () => {
    hookMocks.createConversation.mockResolvedValueOnce(createConversationResponse());
    hookMocks.createRun.mockResolvedValueOnce(createRunResponse());
    hookMocks.startRunStream.mockImplementationOnce(({ onEvent }) => {
      onEvent(
        createRunEventResponse({
          event_type: "run.started",
          sequence_number: 2,
        }),
      );
      onEvent(
        createRunEventResponse({
          event_type: "output.text_delta",
          payload: { text: "Hello" },
          sequence_number: 3,
        }),
      );
      onEvent(
        createRunEventResponse({
          event_type: "output.text_delta",
          payload: { text: " team" },
          sequence_number: 4,
        }),
      );
      onEvent(
        createRunEventResponse({
          event_type: "run.succeeded",
          sequence_number: 5,
        }),
      );

      return Promise.resolve();
    });

    render(<ChatRunsWorkspace />);
    await createConversation();

    fireEvent.click(screen.getByRole("button", { name: "Start run" }));

    await waitFor(() => expect(screen.getByText("Hello team")).toBeTruthy());
    expect(screen.getByText("succeeded")).toBeTruthy();
  });
});

async function createConversation() {
  fireEvent.change(screen.getByLabelText("Agent ID"), {
    target: { value: "agent-1" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Create conversation" }));

  await waitFor(() => expect(hookMocks.createConversation).toHaveBeenCalledTimes(1));
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
    content: "Hello team",
    conversation_id: "conversation-1",
    created_at: "2026-06-23T00:00:00Z",
    id: "message-1",
    role: "user",
    sequence_number: 1,
    status: "created",
    team_id: "team-1",
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
