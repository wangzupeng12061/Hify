"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  appendConversationMessage,
  createConversation,
  listConversationMessages,
  submitMessageFeedback,
} from "./api";
import type { ListConversationMessagesInput } from "./types";

export const conversationQueryKeys = {
  all: ["conversations"] as const,
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
  return useMutation({
    mutationFn: createConversation,
    mutationKey: conversationMutationKeys.createConversation,
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
      await queryClient.invalidateQueries({
        queryKey: [...conversationQueryKeys.all, "messages", request.conversationId],
      });
    },
  });
}

export function useSubmitMessageFeedback() {
  return useMutation({
    mutationFn: submitMessageFeedback,
    mutationKey: conversationMutationKeys.submitFeedback,
  });
}
