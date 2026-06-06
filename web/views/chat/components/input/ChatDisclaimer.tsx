"use client";

import { useTranslation } from "react-i18next";

export const ChatDisclaimer = () => {
  const { t } = useTranslation();

  return (
    <p className="m-0 mt-2.5 text-center text-[11px] text-[#a89f96]">
      {t("chat.disclaimer")}
    </p>
  );
};
