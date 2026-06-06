"use client";

import Image from "next/image";
import Link from "next/link";
import { useTranslation } from "react-i18next";
import { IMAGES } from "../../configs/images";

export const Header = () => {
  const { t } = useTranslation();

  return (
    <div className="flex items-center justify-between gap-3 mb-8 flex-wrap">
      <Link href="/" className="flex items-center">
        <Image
          src={IMAGES.lexCompanion.logo}
          alt={t("common.logoAlt")}
          width={36}
          height={36}
          className="w-9 h-9 object-contain transition-transform hover:scale-110"
        />
      </Link>

      <div className="flex items-center gap-2">
        <Link
          href="/"
          className="flex items-center gap-2 px-4 py-2 bg-transparent border border-gray-200 rounded-full text-gray-600 text-sm font-medium hover:border-indigo-500 hover:text-indigo-600 transition-all"
        >
          <i className="fas fa-arrow-right text-xs"></i>
          <span className="hidden sm:inline">{t("signIn.goToHome")}</span>
        </Link>
      </div>
    </div>
  );
};
