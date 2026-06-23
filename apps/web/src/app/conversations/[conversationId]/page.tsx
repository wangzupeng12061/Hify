import { ConversationDetail } from "@/features/conversations/components/conversation-detail";

export default async function ConversationDetailPage({
  params,
}: {
  params: Promise<{ conversationId: string }>;
}) {
  const { conversationId } = await params;

  return <ConversationDetail conversationId={conversationId} />;
}
