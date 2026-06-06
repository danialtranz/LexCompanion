import type { ApiEnvelope } from "@/hooks/useDocumentHook";
import type { UserConversationData } from "@/hooks/useUserConversation";
import { translate as t } from "@/locale/translate";
import type { BotMessage } from "../types";
import { formatChatTime } from "./formatChatTime";
import { buildMessageFormFill } from "./formFillHitl";
import { mapRetrievalReferencesToCitations } from "./mapRetrievalReferences";

export function botMessageFromConversationData(
  data: UserConversationData | undefined,
  fallbackMsg?: string,
): BotMessage | null {
  if (!data) return null;
  const content = (data.answer ?? data.message ?? "").trim();
  const formFill = buildMessageFormFill(data);
  if (!content && !formFill) return null;

  return {
    id: `bot-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`,
    type: "bot",
    content: content || (data.message as string) || "",
    time: formatChatTime(),
    citations: mapRetrievalReferencesToCitations(data.reference ?? []),
    formFill,
  };
}

export function errorBotMessage(content: string): BotMessage {
  return {
    id: `bot-error-${Date.now()}`,
    type: "bot",
    content,
    time: formatChatTime(),
    citations: [],
    error: true,
  };
}

export function parseConversationResult(
  res: ApiEnvelope<UserConversationData>,
): { bot: BotMessage | null; error: BotMessage | null } {
  if (res.code === 200) {
    const bot = botMessageFromConversationData(res.data, res.msg);
    if (bot) return { bot, error: null };
    return {
      bot: null,
      error: errorBotMessage(
        res.msg || t("chat.messages.noSystemResponse"),
      ),
    };
  }
  return {
    bot: null,
    error: errorBotMessage(res.msg || t("chat.messages.noSystemResponse")),
  };
}
