"use client";

import { useCallback, useMemo, useState, type FormEvent } from "react";

import {
  useAppendConversationMessage,
  useConversationMessages,
  useCreateConversation,
} from "@/features/conversations";
import type { Conversation, ConversationMessage } from "@/features/conversations";
import { useCancelRun, useCreateRun, useRun, useRunEvents, useRunStream } from "@/features/runs";
import { HifyApiError } from "@/lib/api/errors";

import type { Run, RunEvent } from "../types";

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

export function ChatRunsWorkspace() {
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

  const conversationMessagesQuery = useConversationMessages(
    conversation ? { conversationId: conversation.id, limit: 50 } : null,
  );
  const runQuery = useRun(run ? { runId: run.id } : null);
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
  const operationError =
    createConversationMutation.error ??
    appendMessageMutation.error ??
    createRunMutation.error ??
    cancelRunMutation.error ??
    conversationMessagesQuery.error ??
    runQuery.error ??
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
          conversation={conversation}
          form={conversationForm}
          isSubmitting={createConversationMutation.isPending}
          onChange={setConversationForm}
          onSubmit={handleCreateConversation}
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
      <MessageList isLoading={conversationMessagesQuery.isFetching} messages={messages} />
      <RunEventList
        events={events}
        isLoading={runEventsQuery.isFetching}
        onRefresh={() => {
          void runEventsQuery.refetch();
          void runQuery.refetch();
        }}
        run={visibleRun}
      />
    </div>
  );
}

function ConversationForm({
  conversation,
  form,
  isSubmitting,
  onChange,
  onSubmit,
}: {
  conversation: Conversation | null;
  form: ConversationFormState;
  isSubmitting: boolean;
  onChange: (form: ConversationFormState) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <form className="panel form-panel" onSubmit={onSubmit}>
      <p className="panel__eyebrow">Step 1</p>
      <h2>Create conversation</h2>
      <label className="form-field">
        Agent ID
        <input
          name="agentId"
          onChange={(event) => onChange({ ...form, agentId: event.target.value })}
          required
          value={form.agentId}
        />
      </label>
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
