"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ChevronDown } from "lucide-react";
import { useTranslation } from "react-i18next";
import {
  type AppLocale,
  changeAppLocale,
  normalizeLocale,
  SUPPORTED_LOCALES,
} from "@/locale/i18n";
import { LocaleFlag } from "./LocaleFlag";

export const LanguageSwitcher = () => {
  const { i18n, t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [pending, setPending] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const current = normalizeLocale(i18n.resolvedLanguage ?? i18n.language);

  const handleSelect = useCallback(async (locale: AppLocale) => {
    if (locale === current) {
      setOpen(false);
      return;
    }

    setOpen(false);
    setPending(true);
    try {
      await changeAppLocale(locale);
    } finally {
      setPending(false);
    }
  }, [current]);

  useEffect(() => {
    if (!open) return;

    const handlePointerDown = (event: PointerEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setOpen(false);
      }
    };

    document.addEventListener("pointerdown", handlePointerDown);
    return () => document.removeEventListener("pointerdown", handlePointerDown);
  }, [open]);

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-label={t("chat.header.language")}
        aria-haspopup="listbox"
        aria-expanded={open}
        disabled={pending}
        className="flex h-9 items-center gap-1.5 rounded-full border border-[#ebe3d6] bg-white px-2.5 text-xs font-semibold text-[#4a433c] shadow-sm transition-colors cursor-pointer hover:border-[#dcc9a8] hover:text-[#9a6c2b] disabled:cursor-wait disabled:opacity-70"
      >
        <LocaleFlag locale={current} className="h-4 w-4" />
        <ChevronDown
          className={`h-3.5 w-3.5 text-[#8a8178] transition-transform ${open ? "rotate-180" : ""}`}
          strokeWidth={2}
        />
      </button>

      {open && (
        <ul
          role="listbox"
          aria-label={t("chat.header.language")}
          className="absolute right-0 top-[calc(100%+6px)] z-[100] min-w-[148px] overflow-hidden rounded-xl border border-[#ebe3d6] bg-white py-1 shadow-lg"
        >
          {SUPPORTED_LOCALES.map((locale) => {
            const selected = current === locale;
            return (
              <li key={locale}>
                <button
                  type="button"
                  role="option"
                  aria-selected={selected}
                  disabled={pending}
                  onClick={(event) => {
                    event.stopPropagation();
                    void handleSelect(locale);
                  }}
                  className={`flex w-full items-center gap-2.5 px-3 py-2 text-left text-sm transition-colors cursor-pointer disabled:cursor-wait ${
                    selected
                      ? "bg-[#faf3e8] font-semibold text-[#9a6c2b]"
                      : "text-[#4a433c] hover:bg-[#faf7f2]"
                  }`}
                >
                  <LocaleFlag locale={locale} className="h-4 w-4" />
                  <span>{t(`language.${locale}`)}</span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
};
