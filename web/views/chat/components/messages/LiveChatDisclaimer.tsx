"use client";

import { useTranslation } from "react-i18next";

export const LiveChatDisclaimer = () => {
  const { t } = useTranslation();

  return (
    <p className="m-0 mt-2 px-1 text-center text-[10px] leading-relaxed text-[#a89f96]">
      {t("chat.messages.liveDisclaimer")}
    </p>
  );
};
