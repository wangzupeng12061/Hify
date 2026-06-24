"use client";

import { useCallback, useMemo, useState, type FormEvent } from "react";

import {
  useAppendConversationMessage,
  useConversation,
  useConversationMessages,
} from "@/features/conversations";
import { useCreateRun, useRunEvents, useRunStream } from "@/features/runs";
import type { Run, RunEvent } from "@/features/runs";
import { HifyApiError } from "@/lib/api/errors";

type MessageFormState = {
  content: string;
};

const initialMessageForm: MessageFormState = {
  content: "",
};

export function ConversationDetail({ conversationId }: { conversationId: string }) {
  const conversationQuery = useConversation({ conversationId });
  const messagesQuery = useConversationMessages({ conversationId, limit: 50 });
  const appendMessageMutation = useAppendConversationMessage();
  const createRunMutation = useCreateRun();
  const runStream = useRunStream();
  const [messageForm, setMessageForm] = useState(initialMessageForm);
  const [run, setRun] = useState<Run | null>(null);
  const [streamedEvents, setStreamedEvents] = useState<RunEvent[]>([]);
  const [formError, setFormError] = useState<string | null>(null);

  const runEventsQuery = useRunEvents(run ? { runId: run.id, limit: 50 } : null);
  const messages = messagesQuery.data?.items ?? [];
  const events = useMemo(
    () => mergeRunEvents(runEventsQuery.data?.items ?? [], streamedEvents),
    [runEventsQuery.data?.items, streamedEvents],
  );
  const assistantOutput = useMemo(() => getAssistantOutput(events), [events]);
  const operationError =
    conversationQuery.error ??
    messagesQuery.error ??
    appendMessageMutation.error ??
    createRunMutation.error ??
    runEventsQuery.error ??
    runStream.error;

  const handleRunStreamEvent = useCallback((event: RunEvent) => {
    setStreamedEvents((currentEvents) => mergeRunEvents(currentEvents, [event]));
  }, []);

  async function handleAppendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);

    try {
      await appendMessageMutation.mutateAsync({
        content: messageForm.content.trim(),
        conversationId,
        idempotency_key: createIdempotencyKey("message"),
      });
      setMessageForm(initialMessageForm);
      await messagesQuery.refetch();
      await conversationQuery.refetch();

      const createdRun = await createRunMutation.mutateAsync({
        conversation_id: conversationId,
        idempotency_key: createIdempotencyKey("run"),
      });
      setRun(createdRun);
      setStreamedEvents([]);
      void runStream.start({
        onComplete: () => {
          void messagesQuery.refetch();
        },
        onEvent: handleRunStreamEvent,
        runId: createdRun.id,
      });
    } catch {
      return;
    }
  }

  return (
    <div className="page-stack">
      <section className="hero">
        <p className="hero__eyebrow">Conversation detail</p>
        <h2>{conversationQuery.data?.title ?? "Conversation"}</h2>
        <p>
          Continue this conversation with the selected agent. Operational diagnostics stay in the
          Admin Console.
        </p>
      </section>

      {formError ? <ConversationErrorBanner message={formError} /> : null}
      {operationError ? <ConversationErrorBanner error={operationError} /> : null}

      <section className="panel">
        <div className="panel__header">
          <div>
            <p className="panel__eyebrow">Summary</p>
            <h2>Conversation state</h2>
          </div>
          <span className="status-pill">{conversationQuery.data?.status ?? "Loading"}</span>
        </div>
        <dl className="identity-grid">
          <ResultField label="Conversation ID" value={conversationId} />
          <ResultField label="Agent ID" value={conversationQuery.data?.agent_id ?? "Loading"} />
          <ResultField
            label="Messages"
            value={`${conversationQuery.data?.message_count ?? messages.length}`}
          />
          <ResultField label="Stream" value={runStream.status} />
        </dl>
      </section>

      <MessageForm
        form={messageForm}
        isSubmitting={appendMessageMutation.isPending || createRunMutation.isPending}
        onChange={setMessageForm}
        onSubmit={handleAppendMessage}
        streamStatus={runStream.status}
      />

      <AssistantOutputPanel assistantOutput={assistantOutput} streamStatus={runStream.status} />
      <ConversationMessages isLoading={messagesQuery.isFetching} messages={messages} />
    </div>
  );
}

function MessageForm({
  form,
  isSubmitting,
  onChange,
  onSubmit,
  streamStatus,
}: {
  form: MessageFormState;
  isSubmitting: boolean;
  onChange: (form: MessageFormState) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  streamStatus: string;
}) {
  return (
    <form className="panel form-panel" onSubmit={onSubmit}>
      <p className="panel__eyebrow">Message</p>
      <h2>Ask the agent</h2>
      <label className="form-field">
        Message
        <textarea
          name="content"
          onChange={(event) => onChange({ content: event.target.value })}
          required
          rows={6}
          value={form.content}
        />
      </label>
      <button className="button" disabled={isSubmitting} type="submit">
        {isSubmitting ? "Sending..." : "Send and run"}
      </button>
      <p className="form-result">
        <strong>Stream:</strong> <code>{streamStatus}</code>
      </p>
    </form>
  );
}

function AssistantOutputPanel({
  assistantOutput,
  streamStatus,
}: {
  assistantOutput: string;
  streamStatus: string;
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
    </section>
  );
}

function ConversationMessages({
  isLoading,
  messages,
}: {
  isLoading: boolean;
  messages: Array<{ content: string; id: string; role: string; sequence_number: number }>;
}) {
  return (
    <section className="panel">
      <div className="panel__header">
        <div>
          <p className="panel__eyebrow">Messages</p>
          <h2>Transcript</h2>
        </div>
        <span className="status-pill">{isLoading ? "Refreshing" : `${messages.length} messages`}</span>
      </div>
      {messages.length === 0 ? (
        <p className="muted">No messages loaded.</p>
      ) : (
        <ol className="timeline-list">
          {messages.map((message) => (
            <li className="timeline-list__item" key={message.id}>
              <span>
                #{message.sequence_number} {message.role}
              </span>
              <p>{message.content}</p>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

function ConversationErrorBanner({ error, message }: { error?: Error; message?: string }) {
  const errorMessage =
    error instanceof HifyApiError
      ? `${error.message} (${error.code}, ${error.status})`
      : (message ?? error?.message ?? "Conversation operation failed.");

  return (
    <section className="panel panel--danger" role="alert">
      <p className="panel__eyebrow">Conversation error</p>
      <h2>Operation failed</h2>
      <p className="muted">{errorMessage}</p>
    </section>
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
