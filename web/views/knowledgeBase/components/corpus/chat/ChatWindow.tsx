"use client";

import { useCallback, useState } from "react";
import { useTranslation } from "react-i18next";
import { useChatRetrieval } from "@/hooks/useChatHook";
import { ChatContent } from "./ChatContent";
import { ChatInput } from "./ChatInput";
import { ChatReferenceChips } from "./ChatReferenceChips";
import { CHAT_DROP_ZONE_ATTR } from "./types";
import type { ChatReferencesState } from "./useChatReferences";
import type { ChatMessage } from "./types";

export function ChatWindow({
  chatRefs,
  isDragOver,
  isDark,
}: {
  chatRefs: ChatReferencesState;
  isDragOver: boolean;
  isDark: boolean;
}) {
  const { t } = useTranslation();
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const { retrieve, loading } = useChatRetrieval();

  const {
    topics,
    subjects,
    topicIds,
    subjectIds,
    hasReferences,
    removeTopic,
    removeSubject,
    clearAll,
  } = chatRefs;

  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || loading) return;

    const userMsg: ChatMessage = {
      id: `u-${Date.now()}`,
      role: "user",
      content: text,
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");

    try {
      const res = await retrieve({
        query: text,
        reference: { topic_ids: topicIds, subject_ids: subjectIds },
      });

      if (res.code === 200 && res.data?.answer) {
        setMessages((prev) => [
          ...prev,
          {
            id: `a-${Date.now()}`,
            role: "assistant",
            content: res.data!.answer!,
            references: res.data!.reference ?? [],
          },
        ]);
      } else {
        setMessages((prev) => [
          ...prev,
          {
            id: `e-${Date.now()}`,
            role: "assistant",
            content: res.msg || t("corpus.chat.noAnswer"),
            error: res.msg,
          },
        ]);
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: `e-${Date.now()}`,
          role: "assistant",
          content: t("corpus.chat.apiError"),
          error: "network",
        },
      ]);
    }
  }, [input, loading, retrieve, subjectIds, topicIds, t]);

  const filterSummary = hasReferences
    ? [
        topics.length > 0
          ? t("corpus.chat.topicCount", { count: topics.length })
          : null,
        subjects.length > 0
          ? t("corpus.chat.subjectCount", { count: subjects.length })
          : null,
      ]
        .filter(Boolean)
        .join(" · ")
    : t("corpus.chat.fullCorpus");

  return (
    <div
      {...{ [CHAT_DROP_ZONE_ATTR]: "" }}
      className={`flex min-h-[280px] flex-1 flex-col border-t transition-colors ${
        isDark ? "border-slate-700" : "border-slate-100"
      } ${
        isDragOver
          ? isDark
            ? "bg-emerald-950/40 ring-2 ring-inset ring-emerald-500/50"
            : "bg-emerald-50/80 ring-2 ring-inset ring-emerald-400/60"
          : ""
      }`}
    >
      <div
        className={`shrink-0 border-b px-4 py-2.5 ${
          isDark ? "border-slate-700 bg-slate-800/50" : "border-slate-100 bg-slate-50/80"
        }`}
      >
        <h3 className="text-sm font-bold">{t("corpus.chat.title")}</h3>
        <p
          className={`text-[11px] ${isDark ? "text-slate-400" : "text-slate-500"}`}
        >
          {isDragOver
            ? t("corpus.chat.dropHint")
            : t("corpus.chat.scope", { scope: filterSummary })}
        </p>
      </div>

      <div
        className={`shrink-0 border-b px-4 py-3 ${
          isDark ? "border-slate-700/80" : "border-slate-100"
        }`}
      >
        <p
          className={`mb-2 text-[10px] font-bold uppercase tracking-widest ${
            isDark ? "text-slate-500" : "text-slate-400"
          }`}
        >
          {t("corpus.chat.filterTitle")}
        </p>
        <ChatReferenceChips
          topics={topics}
          subjects={subjects}
          onRemoveTopic={removeTopic}
          onRemoveSubject={removeSubject}
          onClearAll={clearAll}
          isDark={isDark}
        />
      </div>

      <ChatContent messages={messages} loading={loading} isDark={isDark} />
      <ChatInput
        value={input}
        onChange={setInput}
        onSend={() => void handleSend()}
        loading={loading}
        isDark={isDark}
      />
    </div>
  );
}
