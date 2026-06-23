import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ChatRunsWorkspace } from "@/features/runs/components/chat-runs-workspace";

const hookMocks = vi.hoisted(() => ({
  appendMessage: vi.fn(),
  cancelRun: vi.fn(),
  createConversation: vi.fn(),
  createRun: vi.fn(),
  refetchRun: vi.fn(),
  refetchRunDiagnostics: vi.fn(),
  refetchRunEvents: vi.fn(),
  runDiagnostics: undefined as unknown,
  runEvents: [] as unknown[],
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
  useRunDiagnostics: () => ({
    data: hookMocks.runDiagnostics,
    error: null,
    isFetching: false,
    refetch: hookMocks.refetchRunDiagnostics,
  }),
  useRunEvents: () => ({
    data: {
      has_more: false,
      items: hookMocks.runEvents,
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
    hookMocks.runDiagnostics = undefined;
    hookMocks.runEvents = [];
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

  it("renders workflow snapshot and runtime steps from run diagnostics", () => {
    hookMocks.runEvents = [
      createRunEventResponse({
        event_type: "diagnostic",
        payload: {
          chunk_type: "workflow_snapshot",
          workflow_definition: createWorkflowDefinition(),
          workflow_id: "workflow-1",
          workflow_name: "Escalation Workflow",
          workflow_version_id: "workflow-version-1",
          workflow_version_number: 2,
        },
        sequence_number: 1,
      }),
      createRunEventResponse({
        event_type: "step.started",
        payload: {
          step_id: "step-1",
          step_type: "llm_call",
          workflow_node_id: "llm",
        },
        sequence_number: 2,
      }),
      createRunEventResponse({
        event_type: "step.succeeded",
        payload: {
          step_id: "step-1",
        },
        sequence_number: 3,
      }),
    ];
    hookMocks.runDiagnostics = createRunDiagnosticsResponse();

    render(<ChatRunsWorkspace />);

    const workflowPanel = screen.getByText("Execution path").closest("section");
    if (workflowPanel === null) {
      throw new Error("Workflow execution panel was not rendered.");
    }

    expect(within(workflowPanel).getByText("Escalation Workflow")).toBeTruthy();
    expect(within(workflowPanel).getByText("Workflow LLM node")).toBeTruthy();
    expect(within(workflowPanel).getByText("type llm_call · node llm · 1200 ms")).toBeTruthy();
    expect(within(workflowPanel).getByText("workflow-version-1")).toBeTruthy();
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

function createWorkflowDefinition() {
  return {
    edges: [{ source_node_id: "start", target_node_id: "llm" }],
    nodes: [
      { config: {}, id: "start", kind: "start" },
      { config: { provider_model_id: "model-1" }, id: "llm", kind: "llm" },
    ],
  };
}

function createRunDiagnosticsResponse() {
  return {
    agent_id: "agent-1",
    agent_version_id: "agent-version-1",
    completed_at: null,
    conversation_id: "conversation-1",
    created_at: "2026-06-23T00:00:00Z",
    duration_ms: null,
    error_code: null,
    error_message: null,
    event_count: 3,
    id: "run-1",
    started_at: "2026-06-23T00:00:00Z",
    status: "running",
    step_count: 1,
    steps: [
      {
        completed_at: "2026-06-23T00:00:01Z",
        duration_ms: 1200,
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
  };
}
