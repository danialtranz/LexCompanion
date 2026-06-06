"use client";

import { X } from "lucide-react";
import { useTranslation } from "react-i18next";

type LiveGuidanceHeaderProps = {
  onClose?: () => void;
};

export const LiveGuidanceHeader = ({ onClose }: LiveGuidanceHeaderProps) => {
  const { t } = useTranslation();

  return (
    <header className="flex h-[52px] shrink-0 items-center justify-between gap-3 border-b border-[#ebe3d6] bg-white px-4">
      <div className="flex min-w-0 items-center gap-2.5">
        <h2 className="m-0 truncate text-sm font-semibold text-[#2c2620]">
          {t("chat.messages.liveGuidanceTitle")}
        </h2>
        <span className="inline-flex shrink-0 items-center gap-1.5 rounded-full border border-[#b8e0c8] bg-[#edf8f1] px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-[#2d7a4a]">
          <span className="relative flex h-1.5 w-1.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#3cb371] opacity-60" />
            <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-[#3cb371]" />
          </span>
          {t("common.live")}
        </span>
      </div>
      {onClose && (
        <button
          type="button"
          aria-label={t("chat.messages.exitLiveMode")}
          onClick={onClose}
          className="grid h-8 w-8 shrink-0 cursor-pointer place-items-center rounded-lg border-0 bg-transparent text-[#8a8178] transition-colors hover:bg-[#faf5ec] hover:text-[#2c2620]"
        >
          <X className="h-4 w-4" strokeWidth={2} />
        </button>
      )}
    </header>
  );
};
