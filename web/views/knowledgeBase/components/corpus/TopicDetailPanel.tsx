"use client";

import { ArrowRight, Download, FileText, Loader2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import {
  useAdminLegalTopicDetail,
  type AdminLegalTopicDetail,
} from "@/hooks/useDocumentHook";
import { AddToChatFilterButton } from "./chat/AddToChatFilterButton";
import { DetailRow, NodeTypeBadge, StatCard } from "./DetailPrimitives";

export function TopicDetailPanel({
  topicId,
  label,
  isExpanded,
  onExpandSubjects,
  isInChatFilter,
  onAddToChatFilter,
  isDark,
}: {
  topicId: string;
  label: string;
  isExpanded: boolean;
  onExpandSubjects: () => void;
  isInChatFilter: boolean;
  onAddToChatFilter: () => void;
  isDark?: boolean;
}) {
  const { t } = useTranslation();
  const { data: envelope, isPending } = useAdminLegalTopicDetail(topicId);
  const detail =
    envelope?.code === 200
      ? (envelope.data as AdminLegalTopicDetail)
      : undefined;

  if (isPending) {
    return (
      <div className="flex items-center gap-2 text-sm text-slate-500">
        <Loader2 className="h-4 w-4 animate-spin" />
        {t("corpus.detail.loadingTopic")}
      </div>
    );
  }

  if (envelope && envelope.code !== 200) {
    return (
      <p className="text-sm text-rose-600">
        {envelope.msg || t("corpus.detail.loadTopicFailed")}
      </p>
    );
  }

  const depth =
    detail?.demuc_count && detail.demuc_count > 0
      ? 2
      : detail?.article_count && detail.article_count > 0
        ? 1
        : 0;

  const exportData = () => {
    const blob = new Blob([JSON.stringify(detail, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `topic-${topicId}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex h-full flex-col">
      <NodeTypeBadge type="topic" />
      <h4 className="mt-3 text-xl font-bold leading-snug text-slate-900">
        {detail?.topic_title_vi || label}
      </h4>

      <div className="mt-4 grid grid-cols-3 gap-2">
        <StatCard
          label={t("corpus.detail.statArticles")}
          value={detail?.article_count?.toLocaleString("vi-VN")}
          tone="emerald"
        />
        <StatCard
          label={t("corpus.detail.statSections")}
          value={detail?.demuc_count?.toLocaleString("vi-VN")}
          tone="sky"
        />
        <StatCard label={t("corpus.detail.statDepth")} value={depth} tone="violet" />
      </div>

      <dl className="mt-4">
        <DetailRow
          icon={FileText}
          label={t("corpus.detail.titleEn")}
          value={detail?.topic_title_en}
        />
        <DetailRow icon={FileText} label={t("corpus.detail.note")} value={detail?.topic_note} />
      </dl>

      <div className="mt-auto space-y-2 pt-6">
        <AddToChatFilterButton
          nodeType="topic"
          label={detail?.topic_title_vi || label}
          isAdded={isInChatFilter}
          onAdd={onAddToChatFilter}
          isDark={isDark}
        />
        <button
          type="button"
          onClick={onExpandSubjects}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-emerald-700"
        >
          {isExpanded
            ? t("corpus.detail.subjectsVisible")
            : t("corpus.detail.viewSubjects")}
          <ArrowRight className="h-4 w-4" />
        </button>
        <button
          type="button"
          onClick={exportData}
          className="flex w-full items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
        >
          <Download className="h-4 w-4" />
          {t("corpus.detail.exportData")}
        </button>
      </div>
    </div>
  );
}
