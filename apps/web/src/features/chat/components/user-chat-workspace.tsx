"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
  type RefObject,
} from "react";
import Link from "next/link";

import { useAgents, type Agent } from "@/features/agents";
import {
  useAppendConversationMessage,
  useConversationMessages,
  useConversations,
  useCreateConversation,
} from "@/features/conversations";
import type { Conversation, ConversationMessage } from "@/features/conversations";
import { useCreateRun, useRunEvents, useRunStream } from "@/features/runs";
import type { Run, RunEvent } from "@/features/runs";
import { useLocalSettings } from "@/features/settings";
import { HifyApiError } from "@/lib/api/errors";

const EMPTY_AGENTS: Agent[] = [];
const EMPTY_CONVERSATIONS: Conversation[] = [];
const PROMPT_SUGGESTIONS = [
  "联网查询 2026 年世界杯最新赛况",
  "总结这个知识库里的关键内容",
  "帮我设计一个自动化工作流",
  "分析最近一次 Agent 运行失败原因",
];

export function UserChatWorkspace() {
  const { settings } = useLocalSettings();
  const agentsQuery = useAgents();
  const conversationsQuery = useConversations({ limit: 20 });
  const createConversationMutation = useCreateConversation();
  const appendMessageMutation = useAppendConversationMessage();
  const createRunMutation = useCreateRun();
  const runStream = useRunStream();
  const [selectedAgentId, setSelectedAgentId] = useState("");
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [composerValue, setComposerValue] = useState("");
  const [localMessages, setLocalMessages] = useState<ConversationMessage[]>([]);
  const [run, setRun] = useState<Run | null>(null);
  const [streamedEvents, setStreamedEvents] = useState<RunEvent[]>([]);
  const [formError, setFormError] = useState<string | null>(null);
  const chatThreadEndRef = useRef<HTMLDivElement | null>(null);

  const agents = agentsQuery.data ?? EMPTY_AGENTS;
  const runnableAgents = useMemo(() => getRunnableAgents(agents), [agents]);
  const configuredDefaultAgentId =
    settings.defaultAgentId &&
    runnableAgents.some((agent) => agent.id === settings.defaultAgentId)
      ? settings.defaultAgentId
      : "";
  const effectiveAgentId = selectedAgentId || configuredDefaultAgentId || runnableAgents[0]?.id || "";
  const conversations = conversationsQuery.data?.items ?? EMPTY_CONVERSATIONS;
  const conversationMessagesQuery = useConversationMessages(
    conversation ? { conversationId: conversation.id, limit: 50 } : null,
  );
  const runEventsQuery = useRunEvents(run ? { runId: run.id, limit: 80 } : null);
  const events = useMemo(
    () => mergeRunEvents(runEventsQuery.data?.items ?? [], streamedEvents),
    [runEventsQuery.data?.items, streamedEvents],
  );
  const assistantOutput = useMemo(() => getAssistantOutput(events), [events]);
  const runActivities = useMemo(() => getRunActivities(events), [events]);
  const sourceReferences = useMemo(() => getSourceReferences(events), [events]);
  const messages = conversationMessagesQuery.data?.items ?? localMessages;
  const isSubmitting =
    createConversationMutation.isPending ||
    appendMessageMutation.isPending ||
    createRunMutation.isPending;
  const operationError =
    agentsQuery.error ??
    conversationsQuery.error ??
    createConversationMutation.error ??
    appendMessageMutation.error ??
    createRunMutation.error ??
    conversationMessagesQuery.error ??
    runEventsQuery.error ??
    runStream.error;

  const handleRunStreamEvent = useCallback((event: RunEvent) => {
    setStreamedEvents((currentEvents) => mergeRunEvents(currentEvents, [event]));
  }, []);

  useEffect(() => {
    if (!settings.autoScroll) {
      return;
    }
    chatThreadEndRef.current?.scrollIntoView?.({ block: "end", behavior: "smooth" });
  }, [assistantOutput, messages.length, settings.autoScroll, runActivities.length]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const content = composerValue.trim();
    if (!content) {
      return;
    }
    setFormError(null);

    const agentId = effectiveAgentId;
    if (!agentId) {
      setFormError("No published agents are available. Ask an admin to publish one first.");
      return;
    }

    try {
      const activeConversation =
        conversation ??
        (await createConversationMutation.mutateAsync({
          agent_id: agentId,
          title: titleFromPrompt(content),
        }));
      if (!conversation) {
        setConversation(activeConversation);
      }

      const message = await appendMessageMutation.mutateAsync({
        content,
        conversationId: activeConversation.id,
        idempotency_key: createIdempotencyKey("message"),
      });
      setLocalMessages((currentMessages) => [...currentMessages, message]);
      setComposerValue("");

      const createdRun = await createRunMutation.mutateAsync({
        conversation_id: activeConversation.id,
        idempotency_key: createIdempotencyKey("run"),
      });
      setRun(createdRun);
      setStreamedEvents([]);
      void runStream.start({
        onComplete: () => {
          void conversationMessagesQuery.refetch();
          void conversationsQuery.refetch();
        },
        onEvent: handleRunStreamEvent,
        runId: createdRun.id,
      });
    } catch {
      return;
    }
  }

  function handleNewChat() {
    runStream.stop();
    setConversation(null);
    setLocalMessages([]);
    setRun(null);
    setStreamedEvents([]);
    setComposerValue("");
    setFormError(null);
  }

  function handleSelectConversation(selectedConversation: Conversation) {
    runStream.stop();
    setConversation(selectedConversation);
    setLocalMessages([]);
    setRun(null);
    setStreamedEvents([]);
    setFormError(null);
    setSelectedAgentId(selectedConversation.agent_id);
  }

  return (
    <div className="chat-shell">
      <ChatSidebar
        conversations={conversations}
        currentConversationId={conversation?.id ?? null}
        isLoading={conversationsQuery.isLoading}
        onNewChat={handleNewChat}
        onSelectConversation={handleSelectConversation}
      />
      <section className="chat-main">
        <ChatHeader
          agentsLoading={agentsQuery.isLoading}
          runnableAgents={runnableAgents}
          selectedAgentId={effectiveAgentId}
          streamStatus={runStream.status}
          onSelectAgent={setSelectedAgentId}
        />

        {formError ? <ChatErrorBanner message={formError} /> : null}
        {operationError ? <ChatErrorBanner error={operationError} /> : null}

        <div className="chat-main__body">
          {conversation || messages.length > 0 || assistantOutput ? (
            <MessageTimeline
              assistantOutput={assistantOutput}
              endRef={chatThreadEndRef}
              isLoading={conversationMessagesQuery.isFetching}
              messages={messages}
              sourceReferences={sourceReferences}
              streamStatus={runStream.status}
            />
          ) : (
            <ChatHome
              onUseSuggestion={setComposerValue}
              suggestions={PROMPT_SUGGESTIONS}
            />
          )}
        </div>

        <ChatComposer
          disabled={isSubmitting}
          onChange={setComposerValue}
          onSubmit={handleSubmit}
          value={composerValue}
        />
      </section>
      <ChatActivityPanel
        activities={settings.showToolActivity ? runActivities : []}
        run={run}
        sources={sourceReferences}
        streamStatus={runStream.status}
      />
    </div>
  );
}

function ChatSidebar({
  conversations,
  currentConversationId,
  isLoading,
  onNewChat,
  onSelectConversation,
}: {
  conversations: Conversation[];
  currentConversationId: string | null;
  isLoading: boolean;
  onNewChat: () => void;
  onSelectConversation: (conversation: Conversation) => void;
}) {
  return (
    <aside className="chat-sidebar" aria-label="Chat workspace">
      <button className="chat-sidebar__new" onClick={onNewChat} type="button">
        New chat
      </button>
      <div className="chat-sidebar__section">
        <p className="chat-sidebar__label">Recent</p>
        {isLoading ? <p className="chat-sidebar__empty">Loading conversations...</p> : null}
        {!isLoading && conversations.length === 0 ? (
          <p className="chat-sidebar__empty">No conversations yet.</p>
        ) : null}
        <div className="chat-sidebar__list">
          {conversations.map((item) => (
            <button
              className="chat-sidebar__item"
              data-active={item.id === currentConversationId}
              key={item.id}
              onClick={() => onSelectConversation(item)}
              type="button"
            >
              <span>{item.title ?? "Untitled chat"}</span>
              <small>{item.status}</small>
            </button>
          ))}
        </div>
      </div>
      <div className="chat-sidebar__footer">
        <Link className="chat-sidebar__admin" href="/admin/agents">
          Admin Console
        </Link>
      </div>
    </aside>
  );
}

function ChatHeader({
  agentsLoading,
  runnableAgents,
  selectedAgentId,
  streamStatus,
  onSelectAgent,
}: {
  agentsLoading: boolean;
  runnableAgents: Agent[];
  selectedAgentId: string;
  streamStatus: string;
  onSelectAgent: (agentId: string) => void;
}) {
  return (
    <header className="chat-header">
      <div>
        <p className="chat-header__eyebrow">Hify Agent</p>
        <h2>Chat Workspace</h2>
      </div>
      <div className="chat-header__actions">
        <select
          aria-label="Agent"
          className="chat-header__select"
          disabled={agentsLoading || runnableAgents.length === 0}
          onChange={(event) => onSelectAgent(event.target.value)}
          value={selectedAgentId}
        >
          <option value="">Select agent</option>
          {runnableAgents.map((agent) => (
            <option key={agent.id} value={agent.id}>
              {agent.name} · v{agent.latest_version_number}
            </option>
          ))}
        </select>
        <span className="chat-header__status">{streamStatus}</span>
      </div>
    </header>
  );
}

function ChatHome({
  onUseSuggestion,
  suggestions,
}: {
  onUseSuggestion: (suggestion: string) => void;
  suggestions: string[];
}) {
  return (
    <div className="chat-home">
      <p className="chat-home__kicker">Phase Two</p>
      <h1>我能为你做什么？</h1>
      <p>直接输入任务，Hify 会创建会话、调用已发布 Agent，并实时展示回复。</p>
      <div className="chat-home__chips">
        {suggestions.map((suggestion) => (
          <button key={suggestion} onClick={() => onUseSuggestion(suggestion)} type="button">
            {suggestion}
          </button>
        ))}
      </div>
    </div>
  );
}

function MessageTimeline({
  assistantOutput,
  endRef,
  isLoading,
  messages,
  sourceReferences,
  streamStatus,
}: {
  assistantOutput: string;
  endRef: RefObject<HTMLDivElement | null>;
  isLoading: boolean;
  messages: ConversationMessage[];
  sourceReferences: SourceReference[];
  streamStatus: string;
}) {
  return (
    <div className="chat-thread">
      {isLoading ? <p className="chat-thread__loading">Refreshing conversation...</p> : null}
      {messages.length === 0 && !assistantOutput ? (
        <p className="chat-thread__empty">Send a message to start this chat.</p>
      ) : null}
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} />
      ))}
      {assistantOutput ? (
        <div className="message-bubble message-bubble--assistant">
          <span>Assistant · {streamStatus}</span>
          <p>{assistantOutput}</p>
          {sourceReferences.length > 0 ? <SourceChips sources={sourceReferences} /> : null}
        </div>
      ) : null}
      <div ref={endRef} />
    </div>
  );
}

function MessageBubble({ message }: { message: ConversationMessage }) {
  const isUser = message.role === "user";
  return (
    <div className={`message-bubble ${isUser ? "message-bubble--user" : "message-bubble--assistant"}`}>
      <span>{isUser ? "You" : "Assistant"}</span>
      <p>{message.content}</p>
    </div>
  );
}

type ToolActivity = {
  detail: string;
  key: string;
  status: string;
  title: string;
};

type SourceReference = {
  key: string;
  provider: string | null;
  snippet: string | null;
  sourceType: string;
  title: string;
  url: string | null;
};

function ChatActivityPanel({
  activities,
  run,
  sources,
  streamStatus,
}: {
  activities: ToolActivity[];
  run: Run | null;
  sources: SourceReference[];
  streamStatus: string;
}) {
  return (
    <aside className="chat-activity-panel" aria-label="Run activity">
      <div className="chat-activity-panel__header">
        <div>
          <p>活动</p>
          <strong>{streamStatus}</strong>
        </div>
        <span>{activities.length + sources.length}</span>
      </div>
      {run ? <p className="chat-activity-panel__run">Run {run.id.slice(0, 8)}</p> : null}
      <section className="chat-activity-panel__section">
        <h3>执行过程</h3>
        {activities.length === 0 ? <p className="chat-activity-panel__empty">暂无活动。</p> : null}
        <div className="activity-timeline">
          {activities.map((activity) => (
            <div className="activity-timeline__item" key={activity.key}>
              <span>{activity.status}</span>
              <strong>{activity.title}</strong>
              <p>{activity.detail}</p>
            </div>
          ))}
        </div>
      </section>
      <section className="chat-activity-panel__section">
        <h3>来源</h3>
        {sources.length === 0 ? <p className="chat-activity-panel__empty">暂无来源。</p> : null}
        <div className="source-list">
          {sources.map((source) => (
            <SourceCard key={source.key} source={source} />
          ))}
        </div>
      </section>
    </aside>
  );
}

function SourceChips({ sources }: { sources: SourceReference[] }) {
  return (
    <div className="source-chips" aria-label="Sources">
      {sources.map((source) =>
        source.url ? (
          <a href={source.url} key={source.key} rel="noreferrer" target="_blank">
            {source.provider ?? source.sourceType}
          </a>
        ) : (
          <span key={source.key}>{source.provider ?? source.sourceType}</span>
        ),
      )}
    </div>
  );
}

function SourceCard({ source }: { source: SourceReference }) {
  const title = source.url ? (
    <a href={source.url} rel="noreferrer" target="_blank">
      {source.title}
    </a>
  ) : (
    <span>{source.title}</span>
  );

  return (
    <article className="source-card">
      <strong>{title}</strong>
      <small>{source.provider ?? source.sourceType}</small>
      {source.snippet ? <p>{source.snippet}</p> : null}
    </article>
  );
}

function ChatComposer({
  disabled,
  onChange,
  onSubmit,
  value,
}: {
  disabled: boolean;
  onChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  value: string;
}) {
  return (
    <form className="chat-composer" onSubmit={onSubmit}>
      <button aria-label="Add context" className="chat-composer__ghost" type="button">
        +
      </button>
      <textarea
        aria-label="Message"
        onChange={(event) => onChange(event.target.value)}
        placeholder="分配一个任务或提问任何问题"
        rows={1}
        value={value}
      />
      <button className="chat-composer__send" disabled={disabled || !value.trim()} type="submit">
        ↑
      </button>
    </form>
  );
}

function ChatErrorBanner({ error, message }: { error?: Error; message?: string }) {
  const errorMessage =
    error instanceof HifyApiError
      ? `${error.message} (${error.code}, ${error.status})`
      : (message ?? error?.message ?? "Chat operation failed.");

  return (
    <section className="chat-error" role="alert">
      <strong>Operation failed</strong>
      <p>{errorMessage}</p>
    </section>
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

function titleFromPrompt(prompt: string): string {
  const normalized = prompt.trim().split(/\s+/).join(" ");
  return normalized.length > 36 ? `${normalized.slice(0, 36)}...` : normalized;
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

function getRunActivities(events: RunEvent[]): ToolActivity[] {
  return events.flatMap((event) => {
    const chunkType = payloadString(event, "chunk_type");
    if (event.event_type === "activity.started" || event.event_type === "activity.completed") {
      return [
        {
          detail: payloadString(event, "detail") ?? "",
          key: `${event.id}:activity`,
          status:
            payloadString(event, "status") ??
            (event.event_type === "activity.completed" ? "completed" : "started"),
          title: payloadString(event, "title") ?? "Agent activity",
        },
      ];
    }
    if (event.event_type === "step.started" && payloadString(event, "step_type") === "tool_call") {
      return [
        {
          detail: `Tool ID: ${payloadString(event, "tool_id") ?? "unknown"}`,
          key: `${event.id}:started`,
          status: "requested",
          title: "Tool call started",
        },
      ];
    }
    if (chunkType === "tool_call_delta") {
      return [
        {
          detail: truncate(payloadString(event, "arguments_delta") ?? "Waiting for arguments", 160),
          key: `${event.id}:delta`,
          status: "planning",
          title: `Model requested tool ${payloadString(event, "name") ?? "unknown"}`,
        },
      ];
    }
    if (chunkType === "tool_result") {
      return [
        {
          detail: `Result size: ${payloadNumber(event, "content_size") ?? 0} characters`,
          key: `${event.id}:result`,
          status: "completed",
          title: `Tool result for ${payloadString(event, "tool_id") ?? "unknown"}`,
        },
      ];
    }
    return [];
  });
}

function getSourceReferences(events: RunEvent[]): SourceReference[] {
  const sourceByKey = new Map<string, SourceReference>();
  events.forEach((event) => {
    if (event.event_type !== "source.discovered") {
      return;
    }
    const url = payloadString(event, "url");
    const title = payloadString(event, "title");
    const sourceType = payloadString(event, "source_type") ?? "source";
    if (!title) {
      return;
    }
    const key = url ?? `${event.run_id}:${event.sequence_number}`;
    if (sourceByKey.has(key)) {
      return;
    }
    sourceByKey.set(key, {
      key,
      provider: payloadString(event, "provider"),
      snippet: payloadString(event, "snippet"),
      sourceType,
      title,
      url,
    });
  });
  return [...sourceByKey.values()];
}

function payloadString(event: RunEvent, key: string): string | null {
  const value = event.payload[key];
  return typeof value === "string" ? value : null;
}

function payloadNumber(event: RunEvent, key: string): number | null {
  const value = event.payload[key];
  return typeof value === "number" ? value : null;
}

function truncate(value: string, maxLength: number): string {
  if (value.length <= maxLength) {
    return value;
  }
  return `${value.slice(0, maxLength - 3)}...`;
}
