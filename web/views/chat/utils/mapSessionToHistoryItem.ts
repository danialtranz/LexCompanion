import type { ChatSessionItem } from "@/hooks/useChatHook";
import { translate as t } from "@/locale/translate";
import type { MessageHistoryItem } from "../components/ChatHistory/types";

function sessionSnippet(session: ChatSessionItem): string {
  const meta = session.metadata ?? {};
  const preview =
    (typeof meta.last_message === "string" && meta.last_message) ||
    (typeof meta.preview === "string" && meta.preview) ||
    (typeof meta.snippet === "string" && meta.snippet);
  if (preview) return preview;
  const title = session.title?.trim();
  if (title) return title;
  return t("chat.history.openToViewDetails");
}

export function mapSessionToHistoryItem(
  session: ChatSessionItem,
): MessageHistoryItem {
  const title =
    session.title?.trim() || t("chat.history.untitledConversation");
  return {
    id: session.id,
    title,
    snippet: sessionSnippet(session),
    updatedAt: session.updated_at ?? session.created_at,
  };
}
