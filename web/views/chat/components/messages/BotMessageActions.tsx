import { Copy, ThumbsDown, ThumbsUp } from "lucide-react";

/** Nút hành động dưới tin bot (UI theo mockup, chưa gắn logic) */
export const BotMessageActions = () => (
  <div className="mt-4 flex items-center gap-1 border-t border-[#f3ece2] pt-3">
    <button
      type="button"
      aria-label="Sao chép"
      className="grid h-8 w-8 place-items-center rounded-lg border-0 bg-transparent text-[#9a9289] transition-colors hover:bg-[#faf5ec] hover:text-[#9a6c2b] cursor-pointer"
    >
      <Copy className="h-4 w-4" strokeWidth={2} />
    </button>
    <button
      type="button"
      aria-label="Hữu ích"
      className="grid h-8 w-8 place-items-center rounded-lg border-0 bg-transparent text-[#9a9289] transition-colors hover:bg-[#faf5ec] hover:text-[#9a6c2b] cursor-pointer"
    >
      <ThumbsUp className="h-4 w-4" strokeWidth={2} />
    </button>
    <button
      type="button"
      aria-label="Không hữu ích"
      className="grid h-8 w-8 place-items-center rounded-lg border-0 bg-transparent text-[#9a9289] transition-colors hover:bg-[#faf5ec] hover:text-[#9a6c2b] cursor-pointer"
    >
      <ThumbsDown className="h-4 w-4" strokeWidth={2} />
    </button>
  </div>
);
