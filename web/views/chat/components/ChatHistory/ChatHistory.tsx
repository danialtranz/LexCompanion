"use client";

import { useMemo, useState } from "react";
import { ChevronDown, Loader2, Trash2 } from "lucide-react";
import { useDeleteChatSession, useChatSessionsList } from "@/hooks/useChatHook";
import { MOCK_CHAT_SESSIONS } from "../../constants/mockChatSessions";
import { mapSessionToHistoryItem } from "../../utils/mapSessionToHistoryItem";
import { DeleteSessionConfirmModal } from "./DeleteSessionConfirmModal";
import { MessageHistory } from "./MessageHistory";
import type { MessageHistoryItem } from "./types";

const PAGE_SIZE = 5;

type ChatHistoryProps = {
  selectedSessionId: string | null;
  onSelectSession: (sessionId: string) => void;
  onDeleteSession?: (sessionId: string) => void;
};

export const ChatHistory = ({
  selectedSessionId,
  onSelectSession,
  onDeleteSession,
}: ChatHistoryProps) => {
  const [page, setPage] = useState(1);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [deletedIds, setDeletedIds] = useState<string[]>([]);
  const [pendingDelete, setPendingDelete] = useState<MessageHistoryItem | null>(
    null,
  );

  const { data, isLoading, isFetching } = useChatSessionsList({
    page,
    page_size: PAGE_SIZE,
  });
  const { deleteSession, loading: deleting } = useDeleteChatSession();

  const apiItems = useMemo((): MessageHistoryItem[] => {
    if (data?.code !== 200 || !data.data?.items?.length) return [];
    return data.data.items.map(mapSessionToHistoryItem);
  }, [data]);

  const items = (apiItems.length > 0 ? apiItems : MOCK_CHAT_SESSIONS).filter(
    (item) => !deletedIds.includes(item.id),
  );

  const total = data?.data?.total ?? 0;
  const hasMore = apiItems.length > 0 && page * PAGE_SIZE < total;
  const showLoadMore = hasMore;

  const requestDeleteSession = (sessionId: string) => {
    const item = items.find((x) => x.id === sessionId);
    if (!item) return;
    setPendingDelete(item);
  };

  const handleConfirmDeleteSession = async () => {
    if (!pendingDelete) return;
    const sessionId = pendingDelete.id;
    if (sessionId.startsWith("mock-")) {
      setDeletedIds((prev) => [...prev, sessionId]);
      onDeleteSession?.(sessionId);
      setPendingDelete(null);
      return;
    }
    try {
      setDeletingId(sessionId);
      const res = await deleteSession(sessionId);
      if (res.code === 200) {
        setDeletedIds((prev) => [...prev, sessionId]);
        onDeleteSession?.(sessionId);
        setPendingDelete(null);
      }
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <aside className="hidden min-h-screen w-full max-w-[320px] shrink-0 flex-col border-r border-[#ebe3d6] bg-[#fffdf9] lg:flex">
      <header className="flex h-[60px] shrink-0 items-center justify-between gap-2 border-b border-[#ebe3d6] px-4">
        <button
          type="button"
          className="flex min-w-0 items-center gap-1 border-0 bg-transparent p-0 text-[14px] font-semibold text-[#2c2620] cursor-pointer"
          aria-haspopup="listbox"
        >
          <span className="truncate">Tất cả hội thoại</span>
          <ChevronDown
            className="h-4 w-4 shrink-0 text-[#8a8178]"
            strokeWidth={2}
          />
        </button>
      </header>

      <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
        <div className="flex-1 overflow-y-auto px-3 py-4">
          {isLoading && apiItems.length === 0 ? (
            <div className="flex items-center justify-center gap-2 py-12 text-[13px] text-[#8a8178]">
              <Loader2 className="h-4 w-4 animate-spin" />
              Đang tải...
            </div>
          ) : (
            <ul className="grid gap-2.5">
              {items.map((item) => (
                <li key={item.id}>
                  <MessageHistory
                    item={item}
                    active={selectedSessionId === item.id}
                    onSelect={onSelectSession}
                    onDelete={requestDeleteSession}
                    deleting={deleting && deletingId === item.id}
                  />
                </li>
              ))}
            </ul>
          )}
        </div>

        {showLoadMore && (
          <div className="shrink-0 border-t border-[#f3ece2] px-3 py-3">
            <button
              type="button"
              disabled={isFetching}
              onClick={() => setPage((p) => p + 1)}
              className="flex h-10 w-full items-center justify-center gap-1.5 rounded-xl border border-[#ebe3d6] bg-white text-[13px] font-medium text-[#6b635a] transition-colors hover:border-[#dcc9a8] hover:text-[#9a6c2b] disabled:opacity-60 cursor-pointer"
            >
              {isFetching ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <ChevronDown className="h-4 w-4" strokeWidth={2} />
              )}
              Xem thêm
            </button>
          </div>
        )}
      </div>
      <DeleteSessionConfirmModal
        open={Boolean(pendingDelete)}
        loading={deleting}
        sessionTitle={pendingDelete?.title || "Hội thoại"}
        onConfirm={handleConfirmDeleteSession}
        onCancel={() => {
          if (deleting) return;
          setPendingDelete(null);
        }}
      />
    </aside>
  );
};
