"use client";

import { Crown } from "lucide-react";
import { useTranslation } from "react-i18next";

export const SidebarUpgrade = () => {
  const { t } = useTranslation();

  return (
    <div className="rounded-xl border border-[#ebe3d6] bg-[#fffaf3] p-3.5 shadow-sm">
      <div className="flex items-start gap-2.5">
        <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-[#f5e6cc] text-[#9a6c2b]">
          <Crown className="h-4 w-4" strokeWidth={2} />
        </span>
        <div className="min-w-0">
          <p className="m-0 text-xs font-bold text-[#2c2620]">
            {t("chat.sidebar.upgradeTitle")}
          </p>
          <p className="mt-0.5 m-0 text-[10px] leading-snug text-[#8a8178]">
            {t("chat.sidebar.upgradeDescription")}
          </p>
        </div>
      </div>
      <button
        type="button"
        className="mt-3 h-9 w-full rounded-lg border border-[#dcc9a8] bg-white text-xs font-semibold text-[#9a6c2b] transition-colors hover:bg-[#faf5ec] cursor-pointer"
      >
        {t("chat.sidebar.upgradeButton")}
      </button>
    </div>
  );
};
