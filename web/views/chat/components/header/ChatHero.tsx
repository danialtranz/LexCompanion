"use client";

import { useTranslation } from "react-i18next";

export const ChatHero = () => {
  const { t } = useTranslation();

  return (
    <div className="flex flex-col items-center justify-center py-16 text-center lg:py-24">
      <div
        aria-hidden
        className="mb-6 grid h-20 w-20 place-items-center rounded-full bg-[#f5ebe0] text-5xl text-[#c9a06a]"
      >
        ⚖
      </div>
      <h2 className="m-0 max-w-md font-serif text-[26px] font-medium leading-snug text-[#2c2620] sm:text-[30px]">
        {t("chat.hero.greeting")}{" "}
        <span className="font-bold text-[#b8874a]">
          {t("chat.hero.helpYou")}
        </span>
      </h2>
      <p className="mt-3 max-w-sm text-sm leading-relaxed text-[#8a8178]">
        {t("chat.hero.description")}
      </p>
    </div>
  );
};
