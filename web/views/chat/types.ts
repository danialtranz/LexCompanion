export interface ChatSource {
  id: string;
  title: string;
  href?: string;
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
  intro: string;
  steps: string[];
  outro: string;
  time: string;
  sources: ChatSource[];
}

export type ChatMessage = UserMessage | BotMessage;
