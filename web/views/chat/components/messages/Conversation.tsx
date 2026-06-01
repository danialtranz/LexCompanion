import type { ChatCitation, ChatMessage } from "../../types";
import { BotMessageCard } from "./BotMessageCard";
import { ChatLoadingIndicator } from "./ChatLoadingIndicator";
import { UserMessageCard } from "./UserMessageCard";

interface ConversationProps {
  messages: ChatMessage[];
  loading?: boolean;
  selectedCitation?: ChatCitation | null;
  selectedMessageId?: string | null;
  onSelectCitation?: (messageId: string, citation: ChatCitation) => void;
}

export const Conversation = ({
  messages,
  loading = false,
  selectedCitation,
  selectedMessageId,
  onSelectCitation,
}: ConversationProps) => (
  <div className="mx-auto flex w-full max-w-3xl flex-col gap-8">
    {messages.map((message) =>
      message.type === "user" ? (
        <UserMessageCard key={message.id} message={message} />
      ) : (
        <BotMessageCard
          key={message.id}
          message={message}
          selectedCitationId={
            selectedMessageId === message.id ? selectedCitation?.id : undefined
          }
          onSelectCitation={
            onSelectCitation
              ? (citation) => onSelectCitation(message.id, citation)
              : undefined
          }
        />
      ),
    )}
    {loading && <ChatLoadingIndicator />}
  </div>
);
