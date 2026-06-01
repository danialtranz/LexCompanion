import type { DragEvent } from "react";
import type { DocumentListItem } from "@/hooks/useDocumentHook";

export const CHAT_DOCUMENT_DRAG_MIME = "application/x-lex-kb-document";

export const CHAT_DROP_ZONE_ATTR = "data-chat-drop-zone";

export type ChatAttachedDocument = {
  id: string;
  name: string;
  type: string;
  size?: number;
};

export function documentListItemToAttachment(
  item: DocumentListItem,
): ChatAttachedDocument {
  const type = (item.type || item.suffix.replace(/^\./, "") || "file").toUpperCase();
  return {
    id: item.id,
    name: item.name,
    type,
    size: item.size,
  };
}

export function serializeChatDocumentDragPayload(
  doc: ChatAttachedDocument,
): string {
  return JSON.stringify(doc);
}

export function parseChatDocumentDragPayload(
  dataTransfer: DataTransfer,
): ChatAttachedDocument | null {
  const raw = dataTransfer.getData(CHAT_DOCUMENT_DRAG_MIME);
  if (!raw) return null;
  try {
    const data = JSON.parse(raw) as ChatAttachedDocument;
    const id = String(data.id ?? "").trim();
    const name = String(data.name ?? "").trim();
    if (!id || !name) return null;
    return {
      id,
      name,
      type: String(data.type ?? "FILE").trim() || "FILE",
      size: typeof data.size === "number" ? data.size : undefined,
    };
  } catch {
    return null;
  }
}

export function isChatDocumentDragEvent(event: DragEvent): boolean {
  return event.dataTransfer.types.includes(CHAT_DOCUMENT_DRAG_MIME);
}
