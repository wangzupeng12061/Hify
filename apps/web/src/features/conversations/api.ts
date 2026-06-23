import { hifyApiClient, unwrapApiResponse } from "@/lib/api/client";

import type {
  AppendConversationMessageInput,
  Conversation,
  ConversationPage,
  ConversationMessage,
  ConversationMessagePage,
  CreateConversationRequest,
  GetConversationInput,
  ListConversationsInput,
  ListConversationMessagesInput,
  MessageFeedback,
  SubmitMessageFeedbackInput,
} from "./types";

export async function createConversation(
  request: CreateConversationRequest,
): Promise<Conversation> {
  return unwrapApiResponse(
    await hifyApiClient.POST("/conversations", {
      body: request,
    }),
  );
}

export async function listConversations(
  request: ListConversationsInput = {},
): Promise<ConversationPage> {
  return unwrapApiResponse(
    await hifyApiClient.GET("/conversations", {
      params: {
        query: {
          cursor: request.cursor ?? null,
          limit: request.limit ?? 50,
        },
      },
    }),
  );
}

export async function getConversation(request: GetConversationInput): Promise<Conversation> {
  return unwrapApiResponse(
    await hifyApiClient.GET("/conversations/{conversation_id}", {
      params: {
        path: {
          conversation_id: request.conversationId,
        },
      },
    }),
  );
}

export async function listConversationMessages(
  request: ListConversationMessagesInput,
): Promise<ConversationMessagePage> {
  return unwrapApiResponse(
    await hifyApiClient.GET("/conversations/{conversation_id}/messages", {
      params: {
        path: {
          conversation_id: request.conversationId,
        },
        query: {
          cursor: request.cursor ?? null,
          limit: request.limit ?? 50,
        },
      },
    }),
  );
}

export async function appendConversationMessage(
  request: AppendConversationMessageInput,
): Promise<ConversationMessage> {
  const { conversationId, ...body } = request;

  return unwrapApiResponse(
    await hifyApiClient.POST("/conversations/{conversation_id}/messages", {
      body,
      params: {
        path: {
          conversation_id: conversationId,
        },
      },
    }),
  );
}

export async function submitMessageFeedback(
  request: SubmitMessageFeedbackInput,
): Promise<MessageFeedback> {
  const { conversationId, messageId, ...body } = request;

  return unwrapApiResponse(
    await hifyApiClient.PUT(
      "/conversations/{conversation_id}/messages/{message_id}/feedback",
      {
        body,
        params: {
          path: {
            conversation_id: conversationId,
            message_id: messageId,
          },
        },
      },
    ),
  );
}
