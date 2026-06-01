import type { RetrievalReferenceItem } from "@/hooks/useChatHook";

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  references?: RetrievalReferenceItem[];
  error?: string;
};

export type ChatReferenceItem = {
  id: string;
  nodeType: "topic" | "subject";
  label: string;
};

export const CHAT_DROP_ZONE_ATTR = "data-chat-drop-zone";
