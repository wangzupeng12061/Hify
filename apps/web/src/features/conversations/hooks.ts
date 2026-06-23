"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  appendConversationMessage,
  createConversation,
  getConversation,
  listConversations,
  listConversationMessages,
  submitMessageFeedback,
} from "./api";
import type {
  GetConversationInput,
  ListConversationMessagesInput,
  ListConversationsInput,
} from "./types";

export const conversationQueryKeys = {
  all: ["conversations"] as const,
  detail: (request: GetConversationInput) =>
    [...conversationQueryKeys.all, "detail", request.conversationId] as const,
  list: (request: ListConversationsInput) =>
    [
      ...conversationQueryKeys.all,
      "list",
      request.cursor ?? null,
      request.limit ?? 50,
    ] as const,
  messages: (request: ListConversationMessagesInput) =>
    [
      ...conversationQueryKeys.all,
      "messages",
      request.conversationId,
      request.cursor ?? null,
      request.limit ?? 50,
    ] as const,
};

export const conversationMutationKeys = {
  appendMessage: ["conversations", "append-message"] as const,
  createConversation: ["conversations", "create-conversation"] as const,
  submitFeedback: ["conversations", "submit-feedback"] as const,
};

export function useCreateConversation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createConversation,
    mutationKey: conversationMutationKeys.createConversation,
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: [...conversationQueryKeys.all, "list"],
      });
    },
  });
}

export function useConversations(request: ListConversationsInput = {}) {
  return useQuery({
    queryFn: () => listConversations(request),
    queryKey: conversationQueryKeys.list(request),
  });
}

export function useConversation(request: GetConversationInput | null) {
  return useQuery({
    enabled: request !== null,
    queryFn: () => {
      if (request === null) {
        throw new Error("Conversation query requires a conversation ID.");
      }

      return getConversation(request);
    },
    queryKey:
      request === null
        ? [...conversationQueryKeys.all, "detail", "idle"]
        : conversationQueryKeys.detail(request),
  });
}

export function useConversationMessages(request: ListConversationMessagesInput | null) {
  return useQuery({
    enabled: request !== null,
    queryFn: () => {
      if (request === null) {
        throw new Error("Conversation message query requires a conversation ID.");
      }

      return listConversationMessages(request);
    },
    queryKey:
      request === null
        ? [...conversationQueryKeys.all, "messages", "idle"]
        : conversationQueryKeys.messages(request),
  });
}

export function useAppendConversationMessage() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: appendConversationMessage,
    mutationKey: conversationMutationKeys.appendMessage,
    onSuccess: async (_message, request) => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: conversationQueryKeys.detail({ conversationId: request.conversationId }),
        }),
        queryClient.invalidateQueries({
          queryKey: [...conversationQueryKeys.all, "messages", request.conversationId],
        }),
        queryClient.invalidateQueries({
          queryKey: [...conversationQueryKeys.all, "list"],
        }),
      ]);
    },
  });
}

export function useSubmitMessageFeedback() {
  return useMutation({
    mutationFn: submitMessageFeedback,
    mutationKey: conversationMutationKeys.submitFeedback,
  });
}
