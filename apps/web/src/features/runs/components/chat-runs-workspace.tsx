"use client";

import { useMemo, useState, type FormEvent } from "react";

import {
  useAppendConversationMessage,
  useConversationMessages,
  useCreateConversation,
} from "@/features/conversations";
import type { Conversation, ConversationMessage } from "@/features/conversations";
import { useCancelRun, useCreateRun, useRun, useRunEvents } from "@/features/runs";
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
  const [conversationForm, setConversationForm] = useState(initialConversationForm);
  const [messageForm, setMessageForm] = useState(initialMessageForm);
  const [runForm, setRunForm] = useState<RunFormState>(() => ({
    idempotencyKey: createIdempotencyKey("run"),
  }));
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [localMessages, setLocalMessages] = useState<ConversationMessage[]>([]);
  const [run, setRun] = useState<Run | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const conversationMessagesQuery = useConversationMessages(
    conversation ? { conversationId: conversation.id, limit: 50 } : null,
  );
  const runQuery = useRun(run ? { runId: run.id } : null);
  const runEventsQuery = useRunEvents(run ? { runId: run.id, limit: 50 } : null);
  const visibleRun = runQuery.data ?? run;
  const messages = conversationMessagesQuery.data?.items ?? localMessages;
  const events = runEventsQuery.data?.items ?? [];
  const operationError =
    createConversationMutation.error ??
    appendMessageMutation.error ??
    createRunMutation.error ??
    cancelRunMutation.error ??
    conversationMessagesQuery.error ??
    runQuery.error ??
    runEventsQuery.error;

  async function handleCreateConversation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);

    try {
      const createdConversation = await createConversationMutation.mutateAsync({
        agent_id: conversationForm.agentId.trim(),
        title: conversationForm.title.trim() || null,
      });
      setConversation(createdConversation);
      setLocalMessages([]);
      setRun(null);
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
      setRunForm({ idempotencyKey: createIdempotencyKey("run") });
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
          This first chat surface uses REST APIs for the MVP path. Streaming execution will be
          layered in after the SSE transport is hardened.
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
        />
      </section>

      <RunSummary conversation={conversation} run={visibleRun} />
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
}: {
  form: RunFormState;
  isCancelling: boolean;
  isSubmitting: boolean;
  onCancel: () => void;
  onChange: (form: RunFormState) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  run: Run | null;
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
    </form>
  );
}

function RunSummary({ conversation, run }: { conversation: Conversation | null; run: Run | null }) {
  const summaryItems = useMemo(
    () => [
      { label: "Conversation ID", value: conversation?.id ?? "Not created" },
      { label: "Agent ID", value: conversation?.agent_id ?? "Not available" },
      { label: "Run ID", value: run?.id ?? "Not started" },
      { label: "Run status", value: run?.status ?? "Not started" },
      { label: "Run events", value: run ? `${run.event_count}` : "0" },
    ],
    [conversation, run],
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
