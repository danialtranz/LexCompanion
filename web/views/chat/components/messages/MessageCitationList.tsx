import { BookMarked, ChevronRight } from "lucide-react";
import type { ChatCitation } from "../../types";

interface MessageCitationListProps {
  citations: ChatCitation[];
  selectedCitationId?: string;
  onSelectCitation: (citation: ChatCitation) => void;
}

export const MessageCitationList = ({
  citations,
  selectedCitationId,
  onSelectCitation,
}: MessageCitationListProps) => {
  if (citations.length === 0) return null;

  return (
    <div className="mt-4">
      <div className="mb-2.5 flex items-center gap-2 text-xs text-[#8a8178]">
        <BookMarked className="h-3.5 w-3.5 shrink-0 text-[#9a6c2b]" strokeWidth={2} />
        <span>
          Phản hồi dựa trên{" "}
          <span className="font-semibold text-[#5c554d]">
            {citations.length} nguồn trích dẫn
          </span>
        </span>
      </div>

      <ul className="m-0 flex list-none flex-col gap-2 p-0">
        {citations.map((citation) => {
          const isSelected = selectedCitationId === citation.id;

          return (
            <li key={citation.id}>
              <button
                type="button"
                onClick={() => onSelectCitation(citation)}
                className={`flex w-full items-center gap-3 rounded-xl border px-3.5 py-3 text-left transition-all ${
                  isSelected
                    ? "border-[#d4a96a] bg-[#fff8ec] shadow-[0_2px_12px_rgba(155,108,43,0.12)]"
                    : "border-[#ebe3d6] bg-white hover:border-[#dcc9a8] hover:bg-[#fffdf9]"
                }`}
              >
                <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-gradient-to-br from-[#e8c98a] to-[#c9a06a] text-sm font-bold text-white shadow-sm">
                  {citation.index}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="line-clamp-2 text-sm font-medium leading-snug text-[#2c2620]">
                    <span className="text-[#9a6c2b]">[{citation.index}]</span>{" "}
                    {citation.title}
                  </span>
                  {citation.meta && (
                    <span className="mt-1 block line-clamp-1 text-xs text-[#8a8178]">
                      {citation.meta}
                    </span>
                  )}
                </span>
                <ChevronRight
                  className={`h-4 w-4 shrink-0 ${isSelected ? "text-[#9a6c2b]" : "text-[#c4bbb0]"}`}
                  strokeWidth={2}
                />
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
};
