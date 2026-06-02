"use client";

import {
  type DragEvent,
  type FormEvent,
  type KeyboardEvent,
  useCallback,
  useState,
} from "react";
import { Loader2, SendHorizontal } from "lucide-react";
import type { UploadUserDocumentData } from "@/hooks/useDocumentHook";
import {
  CHAT_DROP_ZONE_ATTR,
  type ChatAttachedDocument,
  isChatDocumentDragEvent,
  parseChatDocumentDragPayload,
} from "@/views/chat/utils/chatDocumentDrag";
import { ChatAttachDropup } from "./ChatAttachDropup";
import { ChatAttachedDocumentChip } from "./ChatAttachedDocumentChip";

interface ChatInputBoxProps {
  value: string;
  onChange: (value: string) => void;
  onSend?: () => void;
  onOpenKnowledgeBase?: () => void;
  onUploadSuccess?: (data: UploadUserDocumentData) => void;
  sessionId?: string | null;
  loading?: boolean;
  disabled?: boolean;
  attachedDocuments?: ChatAttachedDocument[];
  onAttachDocument?: (doc: ChatAttachedDocument) => void;
  onRemoveAttachedDocument?: (docId: string) => void;
}

export const ChatInputBox = ({
  value,
  onChange,
  onSend,
  onOpenKnowledgeBase,
  onUploadSuccess,
  sessionId = null,
  loading = false,
  disabled = false,
  attachedDocuments = [],
  onAttachDocument,
  onRemoveAttachedDocument,
}: ChatInputBoxProps) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const isDisabled = disabled || loading;
  const hasAttachments = attachedDocuments.length > 0;
  const canSend = value.trim().length > 0 || hasAttachments;

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (isDisabled || !canSend) return;
    onSend?.();
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (isDisabled || !canSend) return;
      onSend?.();
    }
  };

  const handleDragEnter = useCallback((event: DragEvent) => {
    if (!isChatDocumentDragEvent(event)) return;
    event.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragOver = useCallback((event: DragEvent) => {
    if (!isChatDocumentDragEvent(event)) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = "copy";
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((event: DragEvent) => {
    if (!isChatDocumentDragEvent(event)) return;
    const next = event.relatedTarget as Node | null;
    if (next && event.currentTarget.contains(next)) return;
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback(
    (event: DragEvent) => {
      if (!isChatDocumentDragEvent(event)) return;
      event.preventDefault();
      setIsDragOver(false);
      if (isDisabled) return;
      const doc = parseChatDocumentDragPayload(event.dataTransfer);
      if (doc) onAttachDocument?.(doc);
    },
    [isDisabled, onAttachDocument],
  );

  return (
    <form
      onSubmit={handleSubmit}
      {...{ [CHAT_DROP_ZONE_ATTR]: "" }}
      onDragEnter={handleDragEnter}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={`relative z-0 flex flex-col overflow-visible rounded-2xl border bg-white shadow-[0_4px_20px_rgba(84,59,28,0.06)] transition-shadow ${
        isDragOver
          ? "border-[#c9a06a] ring-2 ring-[#dcc9a8]/60"
          : "border-[#ebe3d6]"
      }`}
    >
      {hasAttachments && (
        <div className="flex flex-wrap gap-2 border-b border-[#f3ece2] bg-[#fefdfb] px-3 pt-3 pb-2">
          {attachedDocuments.map((doc) => (
            <ChatAttachedDocumentChip
              key={doc.id}
              doc={doc}
              disabled={isDisabled}
              onRemove={() => onRemoveAttachedDocument?.(doc.id)}
            />
          ))}
        </div>
      )}

      <div className="relative flex h-14 items-center gap-2 overflow-visible px-4">
        <input
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isDisabled}
          placeholder={
            hasAttachments
              ? "Hỏi về tài liệu đã gắn hoặc nhập câu hỏi khác..."
              : "Nhập câu hỏi của bạn về pháp luật..."
          }
          className="min-w-0 flex-1 border-0 bg-transparent text-sm text-[#2c2620] outline-none placeholder:text-[#a89f96] disabled:cursor-not-allowed disabled:opacity-60"
        />
        <ChatAttachDropup
          disabled={isDisabled}
          sessionId={sessionId}
          onOpenKnowledgeBase={onOpenKnowledgeBase}
          onUploadSuccess={onUploadSuccess}
        />
        <button
          type="submit"
          disabled={isDisabled || !canSend}
          aria-label="Gửi tin nhắn"
          className="grid h-10 w-10 shrink-0 place-items-center rounded-xl border-0 bg-gradient-to-br from-[#d4a96a] to-[#9a6c2b] text-white shadow-[0_4px_12px_rgba(155,108,43,0.3)] transition-transform hover:-translate-y-px cursor-pointer disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? (
            <Loader2
              className="h-[18px] w-[18px] animate-spin"
              strokeWidth={2.5}
            />
          ) : (
            <SendHorizontal className="h-[18px] w-[18px]" strokeWidth={2.5} />
          )}
        </button>
      </div>
    </form>
  );
};
