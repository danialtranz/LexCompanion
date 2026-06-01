"use client";

import { ArrowLeft, FileText, Hash } from "lucide-react";
import type { AdminLegalArticleItem } from "@/hooks/useDocumentHook";
import { DetailRow, NodeTypeBadge, StatCard } from "./DetailPrimitives";

export function ArticleDetailPanel({
  article,
  label,
  onBack,
}: {
  article?: AdminLegalArticleItem;
  label: string;
  onBack?: () => void;
}) {
  if (!article) {
    return (
      <div>
        {onBack && (
          <button
            type="button"
            onClick={onBack}
            className="mb-3 flex items-center gap-1.5 text-xs font-semibold text-slate-500 transition hover:text-slate-800"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Quay lại subject
          </button>
        )}
        <NodeTypeBadge type="article" />
        <h4 className="mt-3 text-xl font-bold text-slate-900">{label}</h4>
        <p className="mt-3 text-sm text-slate-500">
          Không có dữ liệu chi tiết.
        </p>
      </div>
    );
  }

  return (
    <div>
      {onBack && (
        <button
          type="button"
          onClick={onBack}
          className="mb-3 flex items-center gap-1.5 text-xs font-semibold text-slate-500 transition hover:text-slate-800"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Quay lại subject
        </button>
      )}
      <NodeTypeBadge type="article" />
      <h4 className="mt-3 text-xl font-bold leading-snug text-slate-900">
        {article.article_title || label}
      </h4>

      <div className="mt-4 grid grid-cols-2 gap-2">
        <StatCard
          label="Số ký tự"
          value={article.content_char_len?.toLocaleString("vi-VN")}
          tone="sky"
        />
        <StatCard
          label="Số từ"
          value={article.content_word_count?.toLocaleString("vi-VN")}
          tone="violet"
        />
      </div>

      <dl className="mt-4">
        <DetailRow
          icon={Hash}
          label="Article anchor"
          value={article.article_anchor}
        />
        <DetailRow
          icon={FileText}
          label="Chapter"
          value={article.chapter_title}
        />
        <DetailRow
          icon={FileText}
          label="Subject"
          value={article.subject_title}
        />
        <DetailRow icon={FileText} label="Topic" value={article.topic_title} />

        <DetailRow
          icon={FileText}
          label="Nội dung"
          value={
            article.content_text ? (
              <p className="max-h-64 overflow-y-auto whitespace-pre-wrap rounded-xl bg-slate-50 p-3 text-xs leading-relaxed text-slate-700">
                {article.content_text}
              </p>
            ) : null
          }
        />
      </dl>
    </div>
  );
}
