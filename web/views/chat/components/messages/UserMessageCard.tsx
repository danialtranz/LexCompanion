import type { UserMessage as UserMessageType } from "../../types";
import { highlightText } from "./highlightText";

interface UserMessageCardProps {
  message: UserMessageType;
  searchKeyword?: string;
  variant?: "default" | "live";
}

export const UserMessageCard = ({
  message,
  searchKeyword = "",
  variant = "default",
}: UserMessageCardProps) => {
  if (variant === "live") {
    return (
      <div className="flex flex-col gap-1">
        <div className="flex items-center justify-between gap-2 px-0.5">
          <span className="text-xs font-semibold text-[#2c2620]">Bạn</span>
          <span className="shrink-0 text-[10px] text-[#8a8178]">{message.time}</span>
        </div>
        <div className="rounded-xl border border-[#e8dcc8] bg-[#f5efe4] px-3.5 py-3">
          <p className="mb-0 text-[13px] leading-[1.65] text-[#2c2620]">
            {highlightText(message.content, searchKeyword)}
          </p>
        </div>
      </div>
    );
  }

  return (
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
};
