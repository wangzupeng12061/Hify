"use client";

import { useCallback, useMemo, useState, type FormEvent } from "react";

import { useAgents, type Agent } from "@/features/agents";
import {
  useAppendConversationMessage,
  useConversationMessages,
  useCreateConversation,
} from "@/features/conversations";
import type { Conversation, ConversationMessage } from "@/features/conversations";
import {
  useCancelRun,
  useCreateRun,
  useRun,
  useRunDiagnostics,
  useRunEvents,
  useRunStream,
} from "@/features/runs";
import { HifyApiError } from "@/lib/api/errors";

import type { Run, RunDiagnostics, RunEvent } from "../types";

type ConversationFormState = {
  agentId: string;
  title: string;
};

type MessageFormState = {
  content: string;
};

type RunFormState = {
  idempotencyKey: string;
};

const initialConversationForm: ConversationFormState = {
  agentId: "",
  title: "",
};

const initialMessageForm: MessageFormState = {
  content: "",
};

const EMPTY_AGENTS: Agent[] = [];

export function ChatRunsWorkspace() {
  const agentsQuery = useAgents();
  const createConversationMutation = useCreateConversation();
  const appendMessageMutation = useAppendConversationMessage();
  const createRunMutation = useCreateRun();
  const cancelRunMutation = useCancelRun();
  const runStream = useRunStream();
  const [conversationForm, setConversationForm] = useState(initialConversationForm);
  const [messageForm, setMessageForm] = useState(initialMessageForm);
  const [runForm, setRunForm] = useState<RunFormState>(() => ({
    idempotencyKey: createIdempotencyKey("run"),
  }));
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [localMessages, setLocalMessages] = useState<ConversationMessage[]>([]);
  const [run, setRun] = useState<Run | null>(null);
  const [streamedEvents, setStreamedEvents] = useState<RunEvent[]>([]);
  const [formError, setFormError] = useState<string | null>(null);
  const agents = agentsQuery.data ?? EMPTY_AGENTS;
  const runnableAgents = useMemo(() => getRunnableAgents(agents), [agents]);

  const conversationMessagesQuery = useConversationMessages(
    conversation ? { conversationId: conversation.id, limit: 50 } : null,
  );
  const runQuery = useRun(run ? { runId: run.id } : null);
  const runDiagnosticsQuery = useRunDiagnostics(run ? { runId: run.id } : null);
  const runEventsQuery = useRunEvents(run ? { runId: run.id, limit: 50 } : null);
  const messages = conversationMessagesQuery.data?.items ?? localMessages;
  const events = useMemo(
    () => mergeRunEvents(runEventsQuery.data?.items ?? [], streamedEvents),
    [runEventsQuery.data?.items, streamedEvents],
  );
  const visibleRun = useMemo(
    () => getVisibleRun(runQuery.data ?? run, events),
    [events, run, runQuery.data],
  );
  const assistantOutput = useMemo(() => getAssistantOutput(events), [events]);
  const usageSummary = useMemo(() => getUsageSummary(events), [events]);
  const workflowExecution = useMemo(
    () => getWorkflowExecution(events, runDiagnosticsQuery.data),
    [events, runDiagnosticsQuery.data],
  );
  const operationError =
    createConversationMutation.error ??
    appendMessageMutation.error ??
    createRunMutation.error ??
    cancelRunMutation.error ??
    agentsQuery.error ??
    conversationMessagesQuery.error ??
    runQuery.error ??
    runDiagnosticsQuery.error ??
    runEventsQuery.error ??
    runStream.error;

  const handleRunStreamEvent = useCallback((event: RunEvent) => {
    setStreamedEvents((currentEvents) => mergeRunEvents(currentEvents, [event]));
  }, []);

  async function handleCreateConversation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);
    runStream.stop();

    try {
      const createdConversation = await createConversationMutation.mutateAsync({
        agent_id: conversationForm.agentId.trim(),
        title: conversationForm.title.trim() || null,
      });
      setConversation(createdConversation);
      setLocalMessages([]);
      setRun(null);
      setStreamedEvents([]);
      setRunForm({ idempotencyKey: createIdempotencyKey("run") });
    } catch {
      return;
    }
  }

  async function handleAppendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);

    if (!conversation) {
      setFormError("Create a conversation before sending a message.");
      return;
    }

    try {
      const message = await appendMessageMutation.mutateAsync({
        content: messageForm.content.trim(),
        conversationId: conversation.id,
        idempotency_key: createIdempotencyKey("message"),
      });
      setLocalMessages((currentMessages) => [...currentMessages, message]);
      setMessageForm(initialMessageForm);
    } catch {
      return;
    }
  }

  async function handleCreateRun(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);

    if (!conversation) {
      setFormError("Create a conversation before starting a run.");
      return;
    }

    try {
      const createdRun = await createRunMutation.mutateAsync({
        conversation_id: conversation.id,
        idempotency_key: runForm.idempotencyKey.trim() || createIdempotencyKey("run"),
      });
      setRun(createdRun);
      setStreamedEvents([]);
      setRunForm({ idempotencyKey: createIdempotencyKey("run") });
      void runStream.start({
        onEvent: handleRunStreamEvent,
        runId: createdRun.id,
      });
    } catch {
      return;
    }
  }

  async function handleCancelRun() {
    setFormError(null);

    if (!visibleRun) {
      setFormError("Start a run before cancelling it.");
      return;
    }

    try {
      const cancelledRun = await cancelRunMutation.mutateAsync({ runId: visibleRun.id });
      setRun(cancelledRun);
      runStream.stop();
      void runQuery.refetch();
      void runDiagnosticsQuery.refetch();
      void runEventsQuery.refetch();
    } catch {
      return;
    }
  }

  return (
    <div className="page-stack">
      <section className="hero">
        <p className="hero__eyebrow">Runs</p>
        <h2>Start a conversation and run an agent.</h2>
        <p>
          This chat surface starts a run through REST, then streams Hify run events through SSE for
          live assistant output and execution diagnostics.
        </p>
      </section>

      {formError ? <RunErrorBanner message={formError} /> : null}
      {operationError ? <RunErrorBanner error={operationError} /> : null}

      <section className="provider-layout">
        <ConversationForm
          agentsLoading={agentsQuery.isLoading}
          conversation={conversation}
          form={conversationForm}
          isSubmitting={createConversationMutation.isPending}
          onChange={setConversationForm}
          onSubmit={handleCreateConversation}
          runnableAgents={runnableAgents}
        />
        <MessageForm
          conversation={conversation}
          form={messageForm}
          isSubmitting={appendMessageMutation.isPending}
          onChange={setMessageForm}
          onSubmit={handleAppendMessage}
        />
        <RunForm
          form={runForm}
          isCancelling={cancelRunMutation.isPending}
          isSubmitting={createRunMutation.isPending}
          onCancel={handleCancelRun}
          onChange={setRunForm}
          onSubmit={handleCreateRun}
          run={visibleRun}
          streamStatus={runStream.status}
        />
      </section>

      <RunSummary
        assistantOutput={assistantOutput}
        conversation={conversation}
        events={events}
        run={visibleRun}
        streamStatus={runStream.status}
      />
      <AssistantOutputPanel
        assistantOutput={assistantOutput}
        streamStatus={runStream.status}
        usageSummary={usageSummary}
      />
      <WorkflowExecutionPanel
        isLoading={runDiagnosticsQuery.isFetching || runEventsQuery.isFetching}
        workflowExecution={workflowExecution}
      />
      <MessageList isLoading={conversationMessagesQuery.isFetching} messages={messages} />
      <RunEventList
        events={events}
        isLoading={runEventsQuery.isFetching}
        onRefresh={() => {
          void runEventsQuery.refetch();
          void runDiagnosticsQuery.refetch();
          void runQuery.refetch();
        }}
        run={visibleRun}
      />
    </div>
  );
}

function ConversationForm({
  agentsLoading,
  conversation,
  form,
  isSubmitting,
  onChange,
  onSubmit,
  runnableAgents,
}: {
  agentsLoading: boolean;
  conversation: Conversation | null;
  form: ConversationFormState;
  isSubmitting: boolean;
  onChange: (form: ConversationFormState) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  runnableAgents: Agent[];
}) {
  return (
    <form className="panel form-panel" onSubmit={onSubmit}>
      <p className="panel__eyebrow">Step 1</p>
      <h2>Create conversation</h2>
      <label className="form-field">
        Agent
        <select
          name="agentId"
          onChange={(event) => onChange({ ...form, agentId: event.target.value })}
          required
          value={form.agentId}
        >
          <option value="">Select a published agent</option>
          {runnableAgents.map((agent) => (
            <option key={agent.id} value={agent.id}>
              {formatAgentOption(agent)}
            </option>
          ))}
        </select>
      </label>
      {agentsLoading ? <p className="muted">Loading published agents...</p> : null}
      {!agentsLoading && runnableAgents.length === 0 ? (
        <p className="muted">No published agents are available. Publish an agent before running chat.</p>
      ) : null}
      <label className="form-field">
        Title
        <input
          name="title"
          onChange={(event) => onChange({ ...form, title: event.target.value })}
          placeholder="Optional"
          value={form.title}
        />
      </label>
      <button className="button" disabled={isSubmitting} type="submit">
        {isSubmitting ? "Creating..." : "Create conversation"}
      </button>
      {conversation ? <ResultLine label="Conversation ID" value={conversation.id} /> : null}
    </form>
  );
}

function MessageForm({
  conversation,
  form,
  isSubmitting,
  onChange,
  onSubmit,
}: {
  conversation: Conversation | null;
  form: MessageFormState;
  isSubmitting: boolean;
  onChange: (form: MessageFormState) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <form className="panel form-panel" onSubmit={onSubmit}>
      <p className="panel__eyebrow">Step 2</p>
      <h2>Send message</h2>
      <label className="form-field">
        User message
        <textarea
          disabled={!conversation}
          name="content"
          onChange={(event) => onChange({ content: event.target.value })}
          required
          rows={6}
          value={form.content}
        />
      </label>
      <button className="button" disabled={!conversation || isSubmitting} type="submit">
        {isSubmitting ? "Sending..." : "Send message"}
      </button>
    </form>
  );
}

function RunForm({
  form,
  isCancelling,
  isSubmitting,
  onCancel,
  onChange,
  onSubmit,
  run,
  streamStatus,
}: {
  form: RunFormState;
  isCancelling: boolean;
  isSubmitting: boolean;
  onCancel: () => void;
  onChange: (form: RunFormState) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  run: Run | null;
  streamStatus: string;
}) {
  return (
    <form className="panel form-panel" onSubmit={onSubmit}>
      <p className="panel__eyebrow">Step 3</p>
      <h2>Create run</h2>
      <label className="form-field">
        Idempotency key
        <input
          name="idempotencyKey"
          onChange={(event) => onChange({ idempotencyKey: event.target.value })}
          required
          value={form.idempotencyKey}
        />
      </label>
      <button className="button" disabled={isSubmitting} type="submit">
        {isSubmitting ? "Starting..." : "Start run"}
      </button>
      <button
        className="button button--secondary"
        disabled={!run || isCancelling}
        onClick={onCancel}
        type="button"
      >
        {isCancelling ? "Cancelling..." : "Cancel run"}
      </button>
      {run ? <ResultLine label="Run ID" value={run.id} /> : null}
      <ResultLine label="Stream status" value={streamStatus} />
    </form>
  );
}

function RunSummary({
  assistantOutput,
  conversation,
  events,
  run,
  streamStatus,
}: {
  assistantOutput: string;
  conversation: Conversation | null;
  events: RunEvent[];
  run: Run | null;
  streamStatus: string;
}) {
  const summaryItems = useMemo(
    () => [
      { label: "Conversation ID", value: conversation?.id ?? "Not created" },
      { label: "Agent ID", value: conversation?.agent_id ?? "Not available" },
      { label: "Run ID", value: run?.id ?? "Not started" },
      { label: "Run status", value: run?.status ?? "Not started" },
      { label: "Stream status", value: streamStatus },
      { label: "Run events", value: `${Math.max(run?.event_count ?? 0, events.length)}` },
      { label: "Assistant chars", value: `${assistantOutput.length}` },
    ],
    [assistantOutput.length, conversation, events.length, run, streamStatus],
  );

  return (
    <section className="panel">
      <div className="panel__header">
        <div>
          <p className="panel__eyebrow">Session summary</p>
          <h2>Conversation and run state</h2>
        </div>
        <span className="status-pill">REST mode</span>
      </div>
      <dl className="identity-grid">
        {summaryItems.map((item) => (
          <ResultField key={item.label} label={item.label} value={item.value} />
        ))}
      </dl>
    </section>
  );
}

function AssistantOutputPanel({
  assistantOutput,
  streamStatus,
  usageSummary,
}: {
  assistantOutput: string;
  streamStatus: string;
  usageSummary: string | null;
}) {
  return (
    <section className="panel">
      <div className="panel__header">
        <div>
          <p className="panel__eyebrow">Assistant</p>
          <h2>Live response</h2>
        </div>
        <span className="status-pill">{streamStatus}</span>
      </div>
      {assistantOutput ? (
        <div className="assistant-output">{assistantOutput}</div>
      ) : (
        <p className="muted">No assistant output streamed yet.</p>
      )}
      {usageSummary ? <p className="form-result">{usageSummary}</p> : null}
    </section>
  );
}

function WorkflowExecutionPanel({
  isLoading,
  workflowExecution,
}: {
  isLoading: boolean;
  workflowExecution: WorkflowExecution;
}) {
  const { snapshot, steps } = workflowExecution;

  return (
    <section className="panel">
      <div className="panel__header">
        <div>
          <p className="panel__eyebrow">Workflow</p>
          <h2>Execution path</h2>
        </div>
        <span className="status-pill">{isLoading ? "Refreshing" : `${steps.length} steps`}</span>
      </div>
      {snapshot ? (
        <dl className="identity-grid">
          <ResultField label="Workflow" value={snapshot.workflowName ?? "Unnamed workflow"} />
          <ResultField label="Version" value={formatOptionalNumber(snapshot.versionNumber)} />
          <ResultField label="Workflow ID" value={snapshot.workflowId ?? "Not available"} />
          <ResultField
            label="Workflow version ID"
            value={snapshot.workflowVersionId ?? "Not available"}
          />
          <ResultField label="Nodes" value={`${snapshot.nodeCount}`} />
          <ResultField label="Edges" value={`${snapshot.edgeCount}`} />
        </dl>
      ) : (
        <p className="muted">
          No workflow snapshot has been recorded for this run. The agent may not be bound to a
          published workflow yet.
        </p>
      )}
      {steps.length > 0 ? (
        <ol className="timeline-list">
          {steps.map((step) => (
            <li className="timeline-list__item" key={`${step.stepId}-${step.sequenceNumber}`}>
              <span>
                #{step.sequenceNumber} {step.status}
              </span>
              <p>{step.label}</p>
              <p className="muted">{formatWorkflowStepDetail(step)}</p>
              {step.errorCode ? (
                <p className="form-result">
                  <strong>Error:</strong> {step.errorCode}
                  {step.errorMessage ? ` · ${step.errorMessage}` : ""}
                </p>
              ) : null}
            </li>
          ))}
        </ol>
      ) : (
        <p className="muted">No workflow runtime steps have been recorded yet.</p>
      )}
    </section>
  );
}

function MessageList({ isLoading, messages }: { isLoading: boolean; messages: ConversationMessage[] }) {
  return (
    <section className="panel">
      <div className="panel__header">
        <div>
          <p className="panel__eyebrow">Messages</p>
          <h2>Conversation transcript</h2>
        </div>
        <span className="status-pill">{isLoading ? "Refreshing" : `${messages.length} messages`}</span>
      </div>
      {messages.length === 0 ? (
        <p className="muted">No messages yet.</p>
      ) : (
        <ol className="timeline-list">
          {messages.map((message) => (
            <li className="timeline-list__item" key={message.id}>
              <span>{message.role}</span>
              <p>{message.content}</p>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

function RunEventList({
  events,
  isLoading,
  onRefresh,
  run,
}: {
  events: RunEvent[];
  isLoading: boolean;
  onRefresh: () => void;
  run: Run | null;
}) {
  return (
    <section className="panel">
      <div className="panel__header">
        <div>
          <p className="panel__eyebrow">Events</p>
          <h2>Run events</h2>
        </div>
        <button
          className="button button--secondary"
          disabled={!run || isLoading}
          onClick={onRefresh}
          type="button"
        >
          {isLoading ? "Refreshing..." : "Refresh events"}
        </button>
      </div>
      {events.length === 0 ? (
        <p className="muted">No run events loaded.</p>
      ) : (
        <ol className="timeline-list">
          {events.map((event) => (
            <li className="timeline-list__item" key={event.id}>
              <span>
                #{event.sequence_number} {event.event_type}
              </span>
              <p>{describeRunEvent(event)}</p>
              <pre>{JSON.stringify(event.payload, null, 2)}</pre>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

function RunErrorBanner({ error, message }: { error?: Error; message?: string }) {
  const errorMessage =
    error instanceof HifyApiError
      ? `${error.message} (${error.code}, ${error.status})`
      : (message ?? error?.message ?? "Run operation failed.");

  return (
    <section className="panel panel--danger" role="alert">
      <p className="panel__eyebrow">Run error</p>
      <h2>Operation failed</h2>
      <p className="muted">{errorMessage}</p>
    </section>
  );
}

function ResultLine({ label, value }: { label: string; value: string }) {
  return (
    <p className="form-result">
      <strong>{label}:</strong> <code>{value}</code>
    </p>
  );
}

function ResultField({ label, value }: { label: string; value: string }) {
  return (
    <div className="identity-field">
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function createIdempotencyKey(prefix: string): string {
  const randomValue =
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID()
      : Math.random().toString(36).slice(2);

  return `${prefix}-${randomValue}`;
}

function getRunnableAgents(agents: Agent[]): Agent[] {
  return agents.filter(
    (agent) => agent.status === "published" && agent.latest_version_number > 0,
  );
}

function formatAgentOption(agent: Agent): string {
  return `${agent.name} · v${agent.latest_version_number}`;
}

function mergeRunEvents(...eventGroups: RunEvent[][]): RunEvent[] {
  const eventByKey = new Map<string, RunEvent>();

  eventGroups.flat().forEach((event) => {
    eventByKey.set(`${event.run_id}:${event.sequence_number}`, event);
  });

  return [...eventByKey.values()].sort(
    (firstEvent, secondEvent) => firstEvent.sequence_number - secondEvent.sequence_number,
  );
}

function getAssistantOutput(events: RunEvent[]): string {
  return events
    .filter((event) => event.event_type === "output.text_delta")
    .map((event) => event.payload.text)
    .filter((text): text is string => typeof text === "string")
    .join("");
}

function getUsageSummary(events: RunEvent[]): string | null {
  const usageEvent = [...events]
    .reverse()
    .find((event) => event.payload.chunk_type === "usage");
  if (!usageEvent) {
    return null;
  }

  const inputTokens = usageEvent.payload.input_tokens;
  const outputTokens = usageEvent.payload.output_tokens;
  const totalTokens = usageEvent.payload.total_tokens;
  if (
    typeof inputTokens !== "number" ||
    typeof outputTokens !== "number" ||
    typeof totalTokens !== "number"
  ) {
    return null;
  }

  return `Usage: ${inputTokens} input / ${outputTokens} output / ${totalTokens} total tokens`;
}

function getVisibleRun(run: Run | null, events: RunEvent[]): Run | null {
  if (!run) {
    return null;
  }

  const status = getRunStatusFromEvents(events) ?? run.status;
  const eventCount = Math.max(run.event_count, events.length);
  return {
    ...run,
    event_count: eventCount,
    status,
  };
}

function getRunStatusFromEvents(events: RunEvent[]): string | null {
  for (const event of [...events].reverse()) {
    if (event.event_type === "run.succeeded") {
      return "succeeded";
    }
    if (event.event_type === "run.failed") {
      return "failed";
    }
    if (event.event_type === "run.cancelled") {
      return "cancelled";
    }
    if (event.event_type === "run.interrupted") {
      return "interrupted";
    }
    if (event.event_type === "run.started") {
      return "running";
    }
  }

  return null;
}

function describeRunEvent(event: RunEvent): string {
  if (event.event_type === "output.text_delta" && typeof event.payload.text === "string") {
    return event.payload.text;
  }

  const chunkType = event.payload.chunk_type;
  if (typeof chunkType === "string") {
    return chunkType.replaceAll("_", " ");
  }

  const errorCode = event.payload.error_code;
  if (typeof errorCode === "string") {
    return `Error: ${errorCode}`;
  }

  return event.event_type;
}

type WorkflowSnapshot = {
  edgeCount: number;
  nodeCount: number;
  versionNumber: number | null;
  workflowId: string | null;
  workflowName: string | null;
  workflowVersionId: string | null;
};

type WorkflowStepView = {
  durationMs: number | null;
  errorCode: string | null;
  errorMessage: string | null;
  label: string;
  nodeId: string | null;
  sequenceNumber: number;
  status: string;
  stepId: string;
  stepType: string;
};

type WorkflowExecution = {
  snapshot: WorkflowSnapshot | null;
  steps: WorkflowStepView[];
};

function getWorkflowExecution(
  events: RunEvent[],
  diagnostics: RunDiagnostics | undefined,
): WorkflowExecution {
  return {
    snapshot: getWorkflowSnapshot(events),
    steps: getWorkflowSteps(events, diagnostics),
  };
}

function getWorkflowSnapshot(events: RunEvent[]): WorkflowSnapshot | null {
  const snapshotEvent = [...events]
    .reverse()
    .find((event) => event.payload.chunk_type === "workflow_snapshot");
  if (!snapshotEvent) {
    return null;
  }

  const definition = snapshotEvent.payload.workflow_definition;
  const workflowId = snapshotEvent.payload.workflow_id;
  const workflowName = snapshotEvent.payload.workflow_name;
  const workflowVersionId = snapshotEvent.payload.workflow_version_id;
  const workflowVersionNumber = snapshotEvent.payload.workflow_version_number;

  return {
    edgeCount: getArrayLengthFromRecord(definition, "edges"),
    nodeCount: getArrayLengthFromRecord(definition, "nodes"),
    versionNumber: typeof workflowVersionNumber === "number" ? workflowVersionNumber : null,
    workflowId: typeof workflowId === "string" ? workflowId : null,
    workflowName: typeof workflowName === "string" ? workflowName : null,
    workflowVersionId: typeof workflowVersionId === "string" ? workflowVersionId : null,
  };
}

function getWorkflowSteps(
  events: RunEvent[],
  diagnostics: RunDiagnostics | undefined,
): WorkflowStepView[] {
  const stepsById = new Map<string, WorkflowStepView>();

  events.forEach((event) => {
    if (event.event_type !== "step.started") {
      return;
    }

    const workflowStep = workflowStepFromStartedEvent(event);
    if (workflowStep) {
      stepsById.set(workflowStep.stepId, workflowStep);
    }
  });

  events.forEach((event) => {
    if (event.event_type !== "step.succeeded" && event.event_type !== "step.failed") {
      return;
    }

    const stepId = getStringPayload(event, "step_id");
    if (!stepId) {
      return;
    }

    const existingStep = stepsById.get(stepId);
    if (!existingStep) {
      return;
    }

    stepsById.set(stepId, {
      ...existingStep,
      errorCode: getStringPayload(event, "error_code") ?? existingStep.errorCode,
      status: event.event_type === "step.succeeded" ? "succeeded" : "failed",
    });
  });

  diagnostics?.steps.forEach((step) => {
    if (!isWorkflowStepName(step.name)) {
      return;
    }

    const existingStep = stepsById.get(step.id);
    stepsById.set(step.id, {
      durationMs: step.duration_ms,
      errorCode: step.error_code,
      errorMessage: step.error_message,
      label: step.name ?? existingStep?.label ?? formatWorkflowStepType(step.step_type),
      nodeId: existingStep?.nodeId ?? null,
      sequenceNumber: step.sequence_number,
      status: step.status,
      stepId: step.id,
      stepType: step.step_type,
    });
  });

  return [...stepsById.values()].sort(
    (firstStep, secondStep) => firstStep.sequenceNumber - secondStep.sequenceNumber,
  );
}

function workflowStepFromStartedEvent(event: RunEvent): WorkflowStepView | null {
  const stepId = getStringPayload(event, "step_id");
  if (!stepId) {
    return null;
  }

  const workflowVersionId = getStringPayload(event, "workflow_version_id");
  const workflowNodeId = getStringPayload(event, "workflow_node_id");
  if (!workflowVersionId && !workflowNodeId) {
    return null;
  }

  const stepType = getStringPayload(event, "step_type") ?? "system";
  return {
    durationMs: null,
    errorCode: null,
    errorMessage: null,
    label: workflowVersionId ? "Workflow runtime" : formatWorkflowStepType(stepType),
    nodeId: workflowNodeId,
    sequenceNumber: event.sequence_number,
    status: "started",
    stepId,
    stepType,
  };
}

function isWorkflowStepName(name: string | null): boolean {
  return typeof name === "string" && name.startsWith("Workflow ");
}

function formatWorkflowStepType(stepType: string): string {
  if (stepType === "llm_call") {
    return "Workflow LLM node";
  }
  if (stepType === "tool_call") {
    return "Workflow tool node";
  }
  return "Workflow step";
}

function formatWorkflowStepDetail(step: WorkflowStepView): string {
  const parts = [`type ${step.stepType}`];
  if (step.nodeId) {
    parts.push(`node ${step.nodeId}`);
  }
  if (step.durationMs !== null) {
    parts.push(`${step.durationMs} ms`);
  }
  return parts.join(" · ");
}

function formatOptionalNumber(value: number | null): string {
  return value === null ? "Not available" : `${value}`;
}

function getStringPayload(event: RunEvent, key: string): string | null {
  const value = event.payload[key];
  return typeof value === "string" ? value : null;
}

function getArrayLengthFromRecord(value: unknown, key: string): number {
  if (!isRecord(value)) {
    return 0;
  }

  const nestedValue = value[key];
  return Array.isArray(nestedValue) ? nestedValue.length : 0;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
