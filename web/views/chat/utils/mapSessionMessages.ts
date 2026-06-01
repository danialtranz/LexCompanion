import type { ChatMessageItem } from "@/hooks/useChatHook";
import type { ChatMessage } from "../types";
import { formatChatTime } from "./formatChatTime";
import { mapRetrievalReferencesToCitations } from "./mapRetrievalReferences";

function formatMessageTime(iso: string | null): string {
  if (!iso) return formatChatTime();
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return formatChatTime();
  return d.toLocaleTimeString("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

function isUserRole(role: string): boolean {
  const r = role.toLowerCase();
  return r === "user" || r === "human";
}

export function mapSessionMessagesToChatMessages(
  items: ChatMessageItem[],
): ChatMessage[] {
  return items.map((msg) => {
    const time = formatMessageTime(msg.created_at);
    if (isUserRole(msg.role)) {
      return {
        id: msg.id,
        type: "user",
        content: msg.content,
        time,
      };
    }
    return {
      id: msg.id,
      type: "bot",
      content: msg.content,
      time,
      citations: mapRetrievalReferencesToCitations(msg.references ?? []),
    };
  });
}
