"use client";

import { BookOpen, ExternalLink, X } from "lucide-react";
import { useTranslation } from "react-i18next";
import type { ChatCitation } from "../../types";
import { highlightText } from "../messages/highlightText";
import { PanelRight } from "./PanelRight";

interface CitationPanelProps {
  citation: ChatCitation | null;
  onClose?: () => void;
  searchKeyword?: string;
}

export const CitationPanel = ({
  citation,
  onClose,
  searchKeyword = "",
}: CitationPanelProps) => {
  const { t } = useTranslation();

  return (
    <PanelRight>
      <div className="flex h-[60px] shrink-0 items-center gap-2.5 border-b border-[#ebe3d6] px-6">
        <BookOpen className="h-4 w-4 shrink-0 text-[#9a6c2b]" strokeWidth={2} />
        <h2 className="m-0 flex-1 text-sm font-semibold text-[#2c2620]">
          {t("chat.citation.title")}
        </h2>
        {citation && (
          <span className="rounded-md bg-[#f5e6cc] px-2 py-0.5 text-xs font-bold text-[#9a6c2b]">
            [{citation.index}]
          </span>
        )}
        {onClose && (
          <button
            type="button"
            aria-label={t("chat.citation.closePanel")}
            onClick={onClose}
            className="grid h-8 w-8 shrink-0 place-items-center rounded-lg border-0 bg-transparent text-[#8a8178] transition-colors hover:bg-[#faf5ec] hover:text-[#2c2620] cursor-pointer"
          >
            <X className="h-4 w-4" strokeWidth={2} />
          </button>
        )}
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5">
        {!citation ? (
          <div className="flex h-full min-h-[200px] flex-col items-center justify-center px-2 text-center">
            <div className="mb-3 grid h-12 w-12 place-items-center rounded-full bg-[#faf5ec] text-[#c9a06a]">
              <BookOpen className="h-5 w-5" strokeWidth={1.75} />
            </div>
            <p className="m-0 text-sm leading-relaxed text-[#8a8178]">
              {t("chat.citation.emptyHint")}
            </p>
          </div>
        ) : (
          <article>
            <h3 className="m-0 text-[15px] font-bold leading-snug text-[#2c2620]">
              {highlightText(citation.title, searchKeyword)}
            </h3>
            {citation.meta && (
              <p className="mt-2 m-0 text-xs leading-relaxed text-[#8a8178]">
                {highlightText(citation.meta, searchKeyword)}
              </p>
            )}
            {citation.href && (
              <a
                href={citation.href}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-3 inline-flex items-center gap-1.5 text-xs font-semibold text-[#9a6c2b] underline-offset-2 transition-colors hover:text-[#7a4d12] hover:underline"
              >
                <ExternalLink className="h-3.5 w-3.5" strokeWidth={2} />
                {t("chat.citation.expandView")}
              </a>
            )}
            <div className="mt-5 rounded-xl border border-[#ebe3d6] bg-[#faf7f2] p-4">
              <p className="m-0 whitespace-pre-wrap text-sm leading-[1.85] text-[#2c2620]">
                {highlightText(
                  citation.excerpt || t("chat.citation.noExcerpt"),
                  searchKeyword,
                )}
              </p>
            </div>
          </article>
        )}
      </div>
    </PanelRight>
  );
};
