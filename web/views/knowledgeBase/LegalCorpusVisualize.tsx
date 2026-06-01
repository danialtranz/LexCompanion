"use client";

import { useCallback, useEffect, useState } from "react";
import { DragToChatGhost } from "./components/corpus/chat/DragToChatGhost";
import type { ChatReferenceItem } from "./components/corpus/chat/types";
import { useChatReferences } from "./components/corpus/chat/useChatReferences";
import { useCorpusDragToChat } from "./components/corpus/chat/useCorpusDragToChat";
import { CorpusDetailSidebar } from "./components/corpus/CorpusDetailSidebar";
import { CorpusGraphHeader } from "./components/corpus/CorpusGraphHeader";
import { LegalCorpusGraphPanel } from "./components/corpus/LegalCorpusGraphPanel";
import { useCorpusGraph } from "./components/corpus/useCorpusGraph";

export function LegalCorpusVisualize() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const chatRefs = useChatReferences();

  const handleDropToChat = useCallback(
    (item: ChatReferenceItem) => {
      chatRefs.addReference(item);
      setSidebarOpen(true);
    },
    [chatRefs],
  );

  const dragToChat = useCorpusDragToChat(handleDropToChat);

  useEffect(() => {
    if (dragToChat.dragging) {
      setSidebarOpen(true);
    }
  }, [dragToChat.dragging]);

  const graph = useCorpusGraph({
    onSelect: () => setSidebarOpen(true),
    consumeIgnoredClick: dragToChat.consumeIgnoredClick,
  });

  const { containerRef, isFullscreen, isDark } = graph;

  const shellClass = isDark
    ? "border-slate-700/80 bg-slate-900/95 text-slate-100"
    : "border-slate-200/80 bg-white/95 text-slate-900";

  return (
    <div
      ref={containerRef}
      className={`overflow-hidden shadow-xl ring-1 backdrop-blur-sm ${
        isFullscreen
          ? "flex h-screen w-screen flex-col rounded-none ring-slate-700/50"
          : "rounded-3xl ring-slate-200/60"
      } ${shellClass}`}
    >
      <CorpusGraphHeader graph={graph} isFullscreen={isFullscreen} />

      <div
        className={`relative flex flex-col lg:flex-row ${
          isFullscreen ? "min-h-0 flex-1" : "min-h-[680px]"
        }`}
      >
        <div className="flex min-h-0 min-w-0 flex-1 flex-col">
          <LegalCorpusGraphPanel
            graph={graph}
            isFullscreen={isFullscreen}
            onNodePointerOver={dragToChat.handleNodePointerOver}
            onNodePointerOut={dragToChat.handleNodePointerOut}
            onGraphPointerDownCapture={dragToChat.handleGraphPointerDownCapture}
          />
        </div>

        <CorpusDetailSidebar
          graph={graph}
          chatRefs={chatRefs}
          isChatDragOver={dragToChat.isOverChat}
          sidebarOpen={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
          isFullscreen={isFullscreen}
          isDark={isDark}
        />

        {dragToChat.dragging && (
          <DragToChatGhost
            item={dragToChat.dragging}
            x={dragToChat.cursor.x}
            y={dragToChat.cursor.y}
          />
        )}

        {!sidebarOpen && (
          <button
            type="button"
            onClick={() => setSidebarOpen(true)}
            className={`absolute bottom-4 right-4 z-20 rounded-xl border px-4 py-2 text-sm font-semibold shadow-lg lg:hidden ${
              isDark
                ? "border-slate-700 bg-slate-800 text-slate-200"
                : "border-slate-200 bg-white text-slate-700"
            }`}
          >
            Mở chi tiết
          </button>
        )}
      </div>
    </div>
  );
}
