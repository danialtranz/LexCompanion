"use client";

import { useTranslation } from "react-i18next";

export const Terms = () => {
  const { t } = useTranslation();

  return (
    <div className="text-center mt-6 text-xs text-gray-400 leading-relaxed">
      <span>{t("signIn.terms.prefix")}</span>
      <a
        href="#terms"
        className="text-indigo-600 hover:text-indigo-700 hover:underline transition-colors"
      >
        {" "}
        {t("signIn.terms.termsOfService")}
      </a>
      <span> {t("signIn.terms.and")}</span>
      <a
        href="#privacy"
        className="text-indigo-600 hover:text-indigo-700 hover:underline transition-colors"
      >
        {" "}
        {t("signIn.terms.privacyPolicy")}
      </a>
    </div>
  );
};
