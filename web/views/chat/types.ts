export interface ChatCitation {
  id: string;
  index: number;
  title: string;
  excerpt: string;
  href?: string;
  meta?: string;
}

export interface UserMessage {
  id: string;
  type: "user";
  content: string;
  time: string;
}

export interface BotMessage {
  id: string;
  type: "bot";
  content: string;
  time: string;
  citations: ChatCitation[];
  error?: boolean;
}

export type ChatMessage = UserMessage | BotMessage;
