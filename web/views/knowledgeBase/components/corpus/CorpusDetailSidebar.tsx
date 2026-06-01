"use client";

import { useRef } from "react";
import { Layers, X } from "lucide-react";
import type { AdminLegalArticleItem } from "@/hooks/useDocumentHook";
import { ArticleDetailPanel } from "./ArticleDetailPanel";
import { ChatWindow } from "./chat/ChatWindow";
import type { ChatReferencesState } from "./chat/useChatReferences";
import { SubjectDetailPanel } from "./SubjectDetailPanel";
import { TopicDetailPanel } from "./TopicDetailPanel";
import type { SelectedNode } from "./types";
import type { useCorpusGraph } from "./useCorpusGraph";

type CorpusGraph = ReturnType<typeof useCorpusGraph>;

export function CorpusDetailSidebar({
  graph,
  chatRefs,
  isChatDragOver,
  sidebarOpen,
  onClose,
  isFullscreen,
  isDark,
}: {
  graph: CorpusGraph;
  chatRefs: ChatReferencesState;
  isChatDragOver: boolean;
  sidebarOpen: boolean;
  onClose: () => void;
  isFullscreen: boolean;
  isDark: boolean;
}) {
  const { selected, setSelected, isSelectedTopicExpanded, expandTopic } =
    graph;

  const { addReference, hasReference } = chatRefs;

  const lastSubjectRef = useRef<SelectedNode | null>(null);

  const addSelectedToChatFilter = () => {
    if (!selected) return;
    if (selected.nodeType !== "topic" && selected.nodeType !== "subject") {
      return;
    }
    addReference({
      id: selected.entityId,
      nodeType: selected.nodeType,
      label: selected.label,
    });
  };

  const handleSelectArticle = (article: AdminLegalArticleItem) => {
    if (selected?.nodeType === "subject") {
      lastSubjectRef.current = selected;
    }
    const title =
      article.article_title ||
      article.article_anchor ||
      `Điều ${article.id}`;
    setSelected({
      nodeType: "article",
      entityId: String(article.id),
      label: title,
      article,
    });
  };

  const handleBackToSubject = () => {
    if (lastSubjectRef.current) {
      setSelected(lastSubjectRef.current);
    }
  };

  if (!sidebarOpen) return null;

  return (
    <aside
      className={`flex w-full flex-col border-t lg:w-[400px] lg:shrink-0 lg:border-l lg:border-t-0 ${
        isFullscreen ? "max-h-[42vh] lg:max-h-none" : "max-h-[85vh] lg:max-h-none"
      } ${isDark ? "border-slate-700/80 bg-slate-900" : "border-slate-100 bg-white"}`}
    >
      <div
        className={`flex items-start justify-between border-b px-5 py-4 ${
          isDark ? "border-slate-700/80" : "border-slate-100"
        }`}
      >
        <div>
          <h3 className="text-base font-bold">Chi tiết & tra cứu</h3>
          <p
            className={`mt-0.5 text-xs ${isDark ? "text-slate-400" : "text-slate-500"}`}
          >
            Giữ & kéo Topic/Subject vào khu chat, hoặc bấm &quot;Thêm vào bộ
            lọc&quot; bên dưới.
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className={`rounded-lg p-1.5 transition ${
            isDark
              ? "text-slate-400 hover:bg-slate-800 hover:text-slate-200"
              : "text-slate-400 hover:bg-slate-100 hover:text-slate-700"
          }`}
          aria-label="Đóng panel"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="max-h-[40vh] shrink-0 overflow-y-auto px-5 py-4 lg:max-h-[35vh]">
        {!selected ? (
          <div className="flex min-h-[160px] flex-col items-center justify-center text-center">
            <div className="mb-3 flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600">
              <Layers className="h-7 w-7" />
            </div>
            <p
              className={`text-sm font-medium ${isDark ? "text-slate-300" : "text-slate-600"}`}
            >
              Chọn một node trên đồ thị
            </p>
            <p
              className={`mt-1 text-xs ${isDark ? "text-slate-500" : "text-slate-400"}`}
            >
              để xem thông tin chi tiết
            </p>
          </div>
        ) : selected.nodeType === "topic" ? (
          <TopicDetailPanel
            topicId={selected.entityId}
            label={selected.label}
            isExpanded={isSelectedTopicExpanded}
            isInChatFilter={hasReference(selected.entityId, "topic")}
            onAddToChatFilter={addSelectedToChatFilter}
            isDark={isDark}
            onExpandSubjects={() => {
              if (!isSelectedTopicExpanded) {
                void expandTopic(selected.entityId);
              }
            }}
          />
        ) : selected.nodeType === "subject" ? (
          <SubjectDetailPanel
            subjectId={selected.entityId}
            label={selected.label}
            isInChatFilter={hasReference(selected.entityId, "subject")}
            onAddToChatFilter={addSelectedToChatFilter}
            isDark={isDark}
            onSelectArticle={handleSelectArticle}
          />
        ) : (
          <ArticleDetailPanel
            article={selected.article}
            label={selected.label}
            onBack={
              lastSubjectRef.current ? handleBackToSubject : undefined
            }
          />
        )}
      </div>

      <ChatWindow
        chatRefs={chatRefs}
        isDragOver={isChatDragOver}
        isDark={isDark}
      />
    </aside>
  );
}
