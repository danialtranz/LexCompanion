import type { ChatMessage } from "../../types";
import { BotMessageCard } from "./BotMessageCard";
import { UserMessageCard } from "./UserMessageCard";

interface ConversationProps {
  messages: ChatMessage[];
}

export const Conversation = ({ messages }: ConversationProps) => (
  <div className="pb-36">
    {messages.map((message) =>
      message.type === "user" ? (
        <UserMessageCard key={message.id} message={message} />
      ) : (
        <BotMessageCard key={message.id} message={message} />
      ),
    )}
  </div>
);
