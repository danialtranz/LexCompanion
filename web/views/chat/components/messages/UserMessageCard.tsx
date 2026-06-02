import type { UserMessage as UserMessageType } from "../../types";
import { highlightText } from "./highlightText";

interface UserMessageCardProps {
  message: UserMessageType;
  searchKeyword?: string;
}

export const UserMessageCard = ({
  message,
  searchKeyword = "",
}: UserMessageCardProps) => (
  <div className="flex items-start gap-3">
    <div className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-linear-to-br from-[#d4a96a] to-[#9a6c2b] text-sm font-semibold text-white">
      N
    </div>
    <div className="min-w-0 flex-1">
      <div className="rounded-2xl border border-[#e8dcc8] bg-[#f3e8d4] px-5 py-4 shadow-sm">
        <div className="flex items-center justify-between gap-3">
          <span className="text-[13px] font-bold text-[#2c2620]">Bạn</span>
          <span className="shrink-0 text-xs text-[#8a8178]">{message.time}</span>
        </div>
        <p className="mb-0 mt-2.5 text-sm leading-[1.8] text-[#2c2620]">
          {highlightText(message.content, searchKeyword)}
        </p>
      </div>
    </div>
  </div>
);
