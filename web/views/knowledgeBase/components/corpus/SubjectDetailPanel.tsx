"use client";

import { ChevronRight, FileText, ListOrdered, Loader2 } from "lucide-react";
import {
  useAdminLegalArticlesList,
  useAdminLegalSubjectDetail,
  type AdminLegalArticleItem,
  type AdminLegalSubjectDetail,
} from "@/hooks/useDocumentHook";
import { CHILD_PAGE_SIZE } from "./constants";
import { AddToChatFilterButton } from "./chat/AddToChatFilterButton";
import { DetailRow, NodeTypeBadge } from "./DetailPrimitives";

export function SubjectDetailPanel({
  subjectId,
  label,
  onSelectArticle,
  isInChatFilter,
  onAddToChatFilter,
  isDark,
}: {
  subjectId: string;
  label: string;
  onSelectArticle: (article: AdminLegalArticleItem) => void;
  isInChatFilter: boolean;
  onAddToChatFilter: () => void;
  isDark?: boolean;
}) {
  const { data: envelope, isPending } = useAdminLegalSubjectDetail(subjectId);
  const { data: articlesEnvelope, isPending: articlesLoading } =
    useAdminLegalArticlesList(
      subjectId,
      { page: 1, page_size: CHILD_PAGE_SIZE },
    );

  const detail =
    envelope?.code === 200
      ? (envelope.data as AdminLegalSubjectDetail)
      : undefined;

  const articles =
    articlesEnvelope?.code === 200
      ? (articlesEnvelope.data?.items ?? [])
      : [];

  if (isPending) {
    return (
      <div className="flex items-center gap-2 text-sm text-slate-500">
        <Loader2 className="h-4 w-4 animate-spin" />
        Đang tải subject…
      </div>
    );
  }

  if (envelope && envelope.code !== 200) {
    return (
      <p className="text-sm text-rose-600">
        {envelope.msg || "Không tải được subject"}
      </p>
    );
  }

  return (
    <div>
      <NodeTypeBadge type="subject" />
      <h4 className="mt-3 text-xl font-bold leading-snug text-slate-900">
        {detail?.subject_title || label}
      </h4>

      <dl className="mt-4">
        <DetailRow icon={FileText} label="Chủ đề" value={detail?.topic_title} />
        <DetailRow
          icon={ListOrdered}
          label="Số subject"
          value={detail?.subject_number}
        />
        <DetailRow
          icon={FileText}
          label="Source URL"
          value={detail?.source_url}
        />
      </dl>

      <div className="mt-4">
        <AddToChatFilterButton
          nodeType="subject"
          label={detail?.subject_title || label}
          isAdded={isInChatFilter}
          onAdd={onAddToChatFilter}
          isDark={isDark}
        />
      </div>

      <div className="mt-6 border-t border-slate-100 pt-4">
        <div className="mb-3 flex items-center justify-between gap-2">
          <h5 className="text-sm font-bold text-slate-800">Danh sách điều</h5>
          {!articlesLoading && articles.length > 0 && (
            <span className="text-xs font-medium text-slate-500">
              {articles.length.toLocaleString("vi-VN")} mục
            </span>
          )}
        </div>

        {articlesLoading ? (
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <Loader2 className="h-4 w-4 animate-spin" />
            Đang tải điều…
          </div>
        ) : articlesEnvelope && articlesEnvelope.code !== 200 ? (
          <p className="text-sm text-rose-600">
            {articlesEnvelope.msg || "Không tải được danh sách điều"}
          </p>
        ) : articles.length === 0 ? (
          <p className="text-sm text-slate-500">Chưa có điều nào.</p>
        ) : (
          <ul className="max-h-56 space-y-1.5 overflow-y-auto pr-1">
            {articles.map((article) => {
              const title =
                article.article_title ||
                article.article_anchor ||
                `Điều ${article.id}`;

              return (
                <li key={article.id}>
                  <button
                    type="button"
                    onClick={() => onSelectArticle(article)}
                    className="flex w-full items-start gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-left text-sm text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
                  >
                    <span className="min-w-0 flex-1 font-medium leading-snug">
                      {title}
                    </span>
                    <ChevronRight className="mt-0.5 h-4 w-4 shrink-0 text-slate-400" />
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
