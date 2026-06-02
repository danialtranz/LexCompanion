import { Loader2, MessageCircle, Trash2 } from "lucide-react";
import { formatHistoryTimestamp } from "../../utils/formatHistoryTimestamp";
import type { MessageHistoryItem } from "./types";

type MessageHistoryProps = {
  item: MessageHistoryItem;
  active?: boolean;
  onSelect: (id: string) => void;
  onDelete?: (id: string) => void;
  deleting?: boolean;
};

export const MessageHistory = ({
  item,
  active = false,
  onSelect,
  onDelete,
  deleting = false,
}: MessageHistoryProps) => (
  <button
    type="button"
    onClick={() => onSelect(item.id)}
    className={`group flex w-full gap-3 rounded-xl border px-3.5 py-3 text-left transition-colors cursor-pointer ${
      active
        ? "border-[#e8d5b8] bg-[#f9f3ee] shadow-[inset_0_0_0_1px_#f0e4d4]"
        : "border-[#ebe3d6] bg-white hover:border-[#e0d0b8] hover:bg-[#fffcf8]"
    }`}
  >
    <span
      className={`mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-lg border ${
        active
          ? "border-[#e8d5b8] bg-[#f5ebe0] text-[#9a6c2b]"
          : "border-[#f0e8dc] bg-[#faf7f2] text-[#8a8178] group-hover:text-[#9a6c2b]"
      }`}
    >
      <MessageCircle className="h-[18px] w-[18px]" strokeWidth={1.75} />
    </span>

    <span className="min-w-0 flex-1">
      <span className="mb-1 flex items-start justify-between gap-2">
        <span
          className={`line-clamp-1 text-[13px] font-semibold leading-snug ${
            active ? "text-[#2c2620]" : "text-[#2c2620]"
          }`}
        >
          {item.title}
        </span>
        <span className="flex shrink-0 items-center gap-1">
          <span className="text-[11px] font-medium text-[#8a8178]">
            {formatHistoryTimestamp(item.updatedAt)}
          </span>
          {onDelete && (
            <button
              type="button"
              disabled={deleting}
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                onDelete(item.id);
              }}
              aria-label="Xoá hội thoại"
              className="grid h-6 w-6 place-items-center rounded-md border border-[#ece2d3] bg-white text-[#9a938a] transition-colors hover:border-[#e2c4a0] hover:text-[#9a6c2b] disabled:opacity-60 cursor-pointer"
            >
              {deleting ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" strokeWidth={2} />
              ) : (
                <Trash2 className="h-3.5 w-3.5" strokeWidth={1.9} />
              )}
            </button>
          )}
        </span>
      </span>
      <span className="line-clamp-2 text-[12px] leading-relaxed text-[#8a8178]">
        {item.snippet}
      </span>
    </span>
  </button>
);
