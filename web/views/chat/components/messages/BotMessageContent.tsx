"use client";

import { type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import type { ChatCitation } from "../../types";
import { highlightText } from "./highlightText";

const IEEE_CITATION_RE = /\[(\d+)\]/g;

interface BotMessageContentProps {
  content: string;
  citations: ChatCitation[];
  selectedCitationId?: string;
  onSelectCitation?: (citation: ChatCitation) => void;
  searchKeyword?: string;
}

function findCitationByIndex(
  citations: ChatCitation[],
  index: number,
): ChatCitation | undefined {
  return citations.find((citation) => citation.index === index);
}

export function renderContentWithIeeeCitations({
  content,
  citations,
  selectedCitationId,
  onSelectCitation,
  searchKeyword = "",
  t,
}: BotMessageContentProps & {
  t: (key: string, options?: Record<string, unknown>) => string;
}): ReactNode[] {
  const parts: ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  const re = new RegExp(IEEE_CITATION_RE.source, "g");

  while ((match = re.exec(content)) !== null) {
    if (match.index > lastIndex) {
      parts.push(
        highlightText(content.slice(lastIndex, match.index), searchKeyword),
      );
    }

    const index = Number.parseInt(match[1], 10);
    const citation = findCitationByIndex(citations, index);

    if (citation && onSelectCitation) {
      const isSelected = selectedCitationId === citation.id;
      parts.push(
        <button
          key={`cite-${match.index}-${index}`}
          type="button"
          onClick={() => onSelectCitation(citation)}
          className={`mx-0.5 inline align-baseline rounded-md px-1.5 py-0.5 text-[12px] font-bold leading-none transition-colors ${
            isSelected
              ? "bg-[#b8874a] text-white shadow-[0_0_0_2px_rgba(184,135,74,0.35)]"
              : "bg-[#f5e6cc] text-[#9a6c2b] hover:bg-[#edd9b0]"
          }`}
          title={citation.title}
          aria-label={t("chat.messages.viewCitation", {
            index,
            title: citation.title,
          })}
          aria-current={isSelected ? "true" : undefined}
        >
          [{index}]
        </button>,
      );
    } else if (citation) {
      parts.push(
        <span
          key={`cite-static-${match.index}-${index}`}
          className="mx-0.5 inline rounded-md bg-[#f5e6cc] px-1.5 py-0.5 text-[12px] font-bold text-[#9a6c2b]"
        >
          [{index}]
        </span>,
      );
    } else {
      parts.push(match[0]);
    }

    lastIndex = re.lastIndex;
  }

  if (lastIndex < content.length) {
    parts.push(highlightText(content.slice(lastIndex), searchKeyword));
  }

  return parts;
}

export const BotMessageContent = ({
  content,
  citations,
  selectedCitationId,
  onSelectCitation,
  searchKeyword,
  error = false,
}: BotMessageContentProps & { error?: boolean }) => {
  const { t } = useTranslation();

  return (
    <div
      className={`whitespace-pre-wrap text-sm leading-[1.8] ${
        error ? "text-[#7a3030]" : "text-[#2c2620]"
      }`}
    >
      {renderContentWithIeeeCitations({
        content,
        citations,
        selectedCitationId,
        onSelectCitation,
        searchKeyword,
        t,
      })}
    </div>
  );
};
