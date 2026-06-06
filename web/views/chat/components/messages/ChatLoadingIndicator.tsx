"use client";

import Image from "next/image";
import { Loader2 } from "lucide-react";
import { useTranslation } from "react-i18next";

const LAWBOT_LOGO = "/images/icons/lex-companion-logo.png";

type ChatLoadingIndicatorProps = {
  variant?: "default" | "live";
};

export const ChatLoadingIndicator = ({
  variant = "default",
}: ChatLoadingIndicatorProps) => {
  const { t } = useTranslation();

  if (variant === "live") {
    return (
      <div className="flex items-center gap-2 rounded-xl border border-[#ebe3d6] bg-white px-3.5 py-3 text-[13px] text-[#8a8178]">
        <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin text-[#2d7a4a]" />
        {t("chat.messages.loadingEditDocument")}
      </div>
    );
  }

  return (
    <div className="flex items-start gap-3">
      <div className="grid h-10 w-10 shrink-0 place-items-center rounded-full border border-[#e8dcc8] bg-white shadow-sm">
        <Image
          src={LAWBOT_LOGO}
          alt={t("common.lawBot")}
          width={24}
          height={24}
          className="h-6 w-6 object-contain"
        />
      </div>
      <div className="flex items-center gap-2.5 rounded-2xl border border-[#ebe3d6] bg-white px-5 py-4 text-sm text-[#8a8178] shadow-sm">
        <Loader2 className="h-4 w-4 animate-spin text-[#9a6c2b]" />
        {t("chat.messages.loadingSearch")}
      </div>
    </div>
  );
};
