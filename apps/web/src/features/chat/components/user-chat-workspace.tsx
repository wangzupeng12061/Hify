"use client";

import { useCallback, useMemo, useState, type FormEvent } from "react";

import { useAgents, type Agent } from "@/features/agents";
import {
  useAppendConversationMessage,
  useConversationMessages,
  useCreateConversation,
} from "@/features/conversations";
import type { Conversation, ConversationMessage } from "@/features/conversations";
import { useCreateRun, useRunEvents, useRunStream } from "@/features/runs";
import type { Run, RunEvent } from "@/features/runs";
import { HifyApiError } from "@/lib/api/errors";

type ConversationFormState = {
  agentId: string;
  title: string;
};

type MessageFormState = {
  content: string;
};

const EMPTY_AGENTS: Agent[] = [];
const initialConversationForm: ConversationFormState = {
  agentId: "",
  title: "",
};
const initialMessageForm: MessageFormState = {
  content: "",
};

export function UserChatWorkspace() {
  const agentsQuery = useAgents();
  const createConversationMutation = useCreateConversation();
  const appendMessageMutation = useAppendConversationMessage();
  const createRunMutation = useCreateRun();
  const runStream = useRunStream();
  const [conversationForm, setConversationForm] = useState(initialConversationForm);
  const [messageForm, setMessageForm] = useState(initialMessageForm);
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
  const runEventsQuery = useRunEvents(run ? { runId: run.id, limit: 50 } : null);
  const messages = conversationMessagesQuery.data?.items ?? localMessages;
  const events = useMemo(
    () => mergeRunEvents(runEventsQuery.data?.items ?? [], streamedEvents),
    [runEventsQuery.data?.items, streamedEvents],
  );
  const assistantOutput = useMemo(() => getAssistantOutput(events), [events]);
  const operationError =
    agentsQuery.error ??
    createConversationMutation.error ??
    appendMessageMutation.error ??
    createRunMutation.error ??
    conversationMessagesQuery.error ??
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
        agent_id: conversationForm.agentId,
        title: conversationForm.title.trim() || null,
      });
      setConversation(createdConversation);
      setLocalMessages([]);
      setRun(null);
      setStreamedEvents([]);
      setMessageForm(initialMessageForm);
    } catch {
      return;
    }
  }

  async function handleSendMessage(event: FormEvent<HTMLFormElement>) {
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

      const createdRun = await createRunMutation.mutateAsync({
        conversation_id: conversation.id,
        idempotency_key: createIdempotencyKey("run"),
      });
      setRun(createdRun);
      setStreamedEvents([]);
      void runStream.start({
        onComplete: () => {
          void conversationMessagesQuery.refetch();
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
        <p className="hero__eyebrow">Chat</p>
        <h2>Use a published agent.</h2>
        <p>
          Start a conversation, send a message, and stream the assistant response. Configuration
          and diagnostics live in the Admin Console.
        </p>
      </section>

      {formError ? <ChatErrorBanner message={formError} /> : null}
      {operationError ? <ChatErrorBanner error={operationError} /> : null}

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
          isSubmitting={appendMessageMutation.isPending || createRunMutation.isPending}
          onChange={setMessageForm}
          onSubmit={handleSendMessage}
          streamStatus={runStream.status}
        />
      </section>

      <AssistantOutputPanel assistantOutput={assistantOutput} streamStatus={runStream.status} />
      <ConversationMessages isLoading={conversationMessagesQuery.isFetching} messages={messages} />
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
      <p className="panel__eyebrow">Conversation</p>
      <h2>Choose an agent</h2>
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
              {agent.name} · v{agent.latest_version_number}
            </option>
          ))}
        </select>
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
      {agentsLoading ? <p className="muted">Loading published agents...</p> : null}
      {!agentsLoading && runnableAgents.length === 0 ? (
        <p className="muted">No published agents are available. Ask an admin to publish one.</p>
      ) : null}
      <button className="button" disabled={isSubmitting} type="submit">
        {isSubmitting ? "Starting..." : conversation ? "Switch conversation" : "Start conversation"}
      </button>
      {conversation ? <ResultLine label="Conversation" value={conversation.id} /> : null}
    </form>
  );
}

function MessageForm({
  conversation,
  form,
  isSubmitting,
  onChange,
  onSubmit,
  streamStatus,
}: {
  conversation: Conversation | null;
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
          disabled={!conversation}
          name="content"
          onChange={(event) => onChange({ content: event.target.value })}
          required
          rows={6}
          value={form.content}
        />
      </label>
      <button className="button" disabled={!conversation || isSubmitting} type="submit">
        {isSubmitting ? "Sending..." : "Send and run"}
      </button>
      <ResultLine label="Stream" value={streamStatus} />
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
  messages: ConversationMessage[];
}) {
  return (
    <section className="panel">
      <div className="panel__header">
        <div>
          <p className="panel__eyebrow">History</p>
          <h2>Current conversation</h2>
        </div>
        <span className="status-pill">{isLoading ? "Refreshing" : `${messages.length} messages`}</span>
      </div>
      {messages.length === 0 ? (
        <p className="muted">No messages yet.</p>
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

function ChatErrorBanner({ error, message }: { error?: Error; message?: string }) {
  const errorMessage =
    error instanceof HifyApiError
      ? `${error.message} (${error.code}, ${error.status})`
      : (message ?? error?.message ?? "Chat operation failed.");

  return (
    <section className="panel panel--danger" role="alert">
      <p className="panel__eyebrow">Chat error</p>
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

function getRunnableAgents(agents: Agent[]): Agent[] {
  return agents.filter(
    (agent) => agent.status === "published" && agent.latest_version_number > 0,
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
