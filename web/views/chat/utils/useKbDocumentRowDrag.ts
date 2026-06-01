"use client";

import { useCallback, type DragEvent } from "react";
import type { DocumentListItem } from "@/hooks/useDocumentHook";
import {
  CHAT_DOCUMENT_DRAG_MIME,
  documentListItemToAttachment,
  serializeChatDocumentDragPayload,
} from "./chatDocumentDrag";

export function isDocumentReadyForChatDrag(item: DocumentListItem): boolean {
  if (item.progress >= 1) return true;
  return String(item.run ?? "").trim() === "1";
}

export function useKbDocumentRowDrag(item: DocumentListItem) {
  const ready = isDocumentReadyForChatDrag(item);

  const onDragStart = useCallback(
    (event: DragEvent) => {
      if (!ready) {
        event.preventDefault();
        return;
      }
      const payload = documentListItemToAttachment(item);
      event.dataTransfer.setData(
        CHAT_DOCUMENT_DRAG_MIME,
        serializeChatDocumentDragPayload(payload),
      );
      event.dataTransfer.effectAllowed = "copy";
    },
    [item, ready],
  );

  return {
    ready,
    draggable: ready,
    onDragStart,
    title: ready
      ? "Kéo vào ô chat để đính kèm tài liệu"
      : "Chờ xử lý xong mới kéo được",
  };
}
