import { QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  useAppendConversationMessage,
  useConversationMessages,
  useCreateConversation,
  useSubmitMessageFeedback,
} from "@/features/conversations";
import { hifyApiClient } from "@/lib/api/client";
import { createHifyQueryClient } from "@/lib/query/query-client";

const apiClientMock = vi.hoisted(() => ({
  GET: vi.fn(),
  POST: vi.fn(),
  PUT: vi.fn(),
}));

vi.mock("@/lib/api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/client")>();

  return {
    ...actual,
    hifyApiClient: apiClientMock,
  };
});

describe("conversation hooks", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("creates conversations with the backend request contract", async () => {
    apiClientMock.POST.mockResolvedValueOnce({
      data: createConversationResponse(),
      response: new Response(null, { status: 201 }),
    });

    const { result } = renderHook(() => useCreateConversation(), {
      wrapper: createQueryWrapper(),
    });

    const conversation = await result.current.mutateAsync({
      agent_id: "agent-1",
      title: "Support chat",
    });

    expect(hifyApiClient.POST).toHaveBeenCalledWith("/conversations", {
      body: {
        agent_id: "agent-1",
        title: "Support chat",
      },
    });
    expect(conversation.id).toBe("conversation-1");
  });

  it("lists conversation messages with path and query params", async () => {
    apiClientMock.GET.mockResolvedValueOnce({
      data: {
        has_more: false,
        items: [createMessageResponse()],
        next_cursor: null,
      },
      response: new Response(null, { status: 200 }),
    });

    const { result } = renderHook(
      () =>
        useConversationMessages({
          conversationId: "conversation-1",
          cursor: "cursor-1",
          limit: 10,
        }),
      { wrapper: createQueryWrapper() },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(hifyApiClient.GET).toHaveBeenCalledWith("/conversations/{conversation_id}/messages", {
      params: {
        path: {
          conversation_id: "conversation-1",
        },
        query: {
          cursor: "cursor-1",
          limit: 10,
        },
      },
    });
  });

  it("appends conversation messages with idempotency keys", async () => {
    apiClientMock.POST.mockResolvedValueOnce({
      data: createMessageResponse(),
      response: new Response(null, { status: 201 }),
    });

    const { result } = renderHook(() => useAppendConversationMessage(), {
      wrapper: createQueryWrapper(),
    });

    await result.current.mutateAsync({
      content: "Hello",
      conversationId: "conversation-1",
      idempotency_key: "message-key",
    });

    expect(hifyApiClient.POST).toHaveBeenCalledWith("/conversations/{conversation_id}/messages", {
      body: {
        content: "Hello",
        idempotency_key: "message-key",
      },
      params: {
        path: {
          conversation_id: "conversation-1",
        },
      },
    });
  });

  it("submits message feedback with path params", async () => {
    apiClientMock.PUT.mockResolvedValueOnce({
      data: {
        comment: "Useful",
        conversation_id: "conversation-1",
        created_at: "2026-06-23T00:00:00Z",
        id: "feedback-1",
        message_id: "message-1",
        rating: "up",
        team_id: "team-1",
        updated_at: "2026-06-23T00:00:00Z",
      },
      response: new Response(null, { status: 200 }),
    });

    const { result } = renderHook(() => useSubmitMessageFeedback(), {
      wrapper: createQueryWrapper(),
    });

    await result.current.mutateAsync({
      comment: "Useful",
      conversationId: "conversation-1",
      messageId: "message-1",
      rating: "up",
    });

    expect(hifyApiClient.PUT).toHaveBeenCalledWith(
      "/conversations/{conversation_id}/messages/{message_id}/feedback",
      {
        body: {
          comment: "Useful",
          rating: "up",
        },
        params: {
          path: {
            conversation_id: "conversation-1",
            message_id: "message-1",
          },
        },
      },
    );
  });
});

function createQueryWrapper() {
  const queryClient = createHifyQueryClient();

  return function QueryWrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
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
    content: "Hello",
    conversation_id: "conversation-1",
    created_at: "2026-06-23T00:00:00Z",
    id: "message-1",
    role: "user",
    sequence_number: 1,
    status: "created",
    team_id: "team-1",
  };
}
