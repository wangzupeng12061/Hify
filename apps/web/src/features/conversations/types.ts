import type { components } from "@/lib/api/generated/schema";

export type AppendConversationMessageRequest =
  components["schemas"]["AppendConversationMessageRequest"];
export type Conversation = components["schemas"]["ConversationResponse"];
export type ConversationMessage = components["schemas"]["ConversationMessageResponse"];
export type ConversationMessagePage =
  components["schemas"]["ConversationMessagePageResponse"];
export type CreateConversationRequest = components["schemas"]["CreateConversationRequest"];
export type MessageFeedback = components["schemas"]["MessageFeedbackResponse"];
export type SubmitMessageFeedbackRequest =
  components["schemas"]["SubmitMessageFeedbackRequest"];

export type AppendConversationMessageInput = AppendConversationMessageRequest & {
  conversationId: string;
};

export type ListConversationMessagesInput = {
  conversationId: string;
  cursor?: string | null;
  limit?: number;
};

export type SubmitMessageFeedbackInput = SubmitMessageFeedbackRequest & {
  conversationId: string;
  messageId: string;
};
