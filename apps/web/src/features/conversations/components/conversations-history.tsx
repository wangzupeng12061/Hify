"use client";

import Link from "next/link";

import { useConversations } from "@/features/conversations";
import { HifyApiError } from "@/lib/api/errors";

export function ConversationsHistory() {
  const conversationsQuery = useConversations({ limit: 50 });
  const conversations = conversationsQuery.data?.items ?? [];

  return (
    <div className="page-stack">
      <section className="hero">
        <p className="hero__eyebrow">Conversations</p>
        <h2>Browse previous agent conversations.</h2>
        <p>
          Open an existing conversation to inspect messages and continue running the agent from
          the current context.
        </p>
      </section>

      {conversationsQuery.error ? <ConversationErrorBanner error={conversationsQuery.error} /> : null}

      <section className="panel">
        <div className="panel__header">
          <div>
            <p className="panel__eyebrow">History</p>
            <h2>Recent conversations</h2>
          </div>
          <span className="status-pill">
            {conversationsQuery.isFetching ? "Refreshing" : `${conversations.length} loaded`}
          </span>
        </div>

        {conversations.length === 0 ? (
          <p className="muted">No conversations found.</p>
        ) : (
          <ol className="timeline-list">
            {conversations.map((conversation) => (
              <li className="timeline-list__item" key={conversation.id}>
                <div className="conversation-list-item">
                  <div>
                    <span>{conversation.status}</span>
                    <h3>{conversation.title ?? "Untitled conversation"}</h3>
                    <p>
                      {conversation.message_count} messages · Agent {conversation.agent_id}
                    </p>
                  </div>
                  <Link className="button button--secondary" href={`/conversations/${conversation.id}`}>
                    Open
                  </Link>
                </div>
              </li>
            ))}
          </ol>
        )}
      </section>
    </div>
  );
}

function ConversationErrorBanner({ error }: { error: Error }) {
  const errorMessage =
    error instanceof HifyApiError
      ? `${error.message} (${error.code}, ${error.status})`
      : error.message;

  return (
    <section className="panel panel--danger" role="alert">
      <p className="panel__eyebrow">Conversation error</p>
      <h2>Operation failed</h2>
      <p className="muted">{errorMessage}</p>
    </section>
  );
}
