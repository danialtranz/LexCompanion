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
  searchKeyword?: string;
  activeFormFillMessageId?: string | null;
  onFormFillSubmit?: (
    messageId: string,
    fieldValues: Record<string, string>,
  ) => void;
  onFormFillReject?: (messageId: string) => void;
  variant?: "default" | "live";
}

export const Conversation = ({
  messages,
  loading = false,
  selectedCitation,
  selectedMessageId,
  onSelectCitation,
  searchKeyword = "",
  activeFormFillMessageId = null,
  onFormFillSubmit,
  onFormFillReject,
  variant = "default",
}: ConversationProps) => (
  <div
    className={
      variant === "live"
        ? "flex w-full flex-col gap-4"
        : "mx-auto flex w-full max-w-3xl flex-col gap-8"
    }
  >
    {messages.map((message) =>
      message.type === "user" ? (
        <UserMessageCard
          key={message.id}
          message={message}
          searchKeyword={searchKeyword}
          variant={variant}
        />
      ) : (
        <BotMessageCard
          key={message.id}
          message={message}
          searchKeyword={searchKeyword}
          variant={variant}
          selectedCitationId={
            selectedMessageId === message.id ? selectedCitation?.id : undefined
          }
          onSelectCitation={
            onSelectCitation
              ? (citation) => onSelectCitation(message.id, citation)
              : undefined
          }
          formFillActive={message.id === activeFormFillMessageId}
          formFillLoading={
            loading && message.id === activeFormFillMessageId
          }
          onFormFillSubmit={onFormFillSubmit}
          onFormFillReject={onFormFillReject}
        />
      ),
    )}
    {loading && <ChatLoadingIndicator variant={variant} />}
  </div>
);
