"use client";

import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import en from "./en";
import vi from "./vi";

export const LOCALE_STORAGE_KEY = "lng";

export type AppLocale = "vi" | "en";

export const SUPPORTED_LOCALES: AppLocale[] = ["vi", "en"];

export const DEFAULT_LOCALE: AppLocale = "vi";

const resources = {
  vi: { translation: vi },
  en: { translation: en },
};

function readStoredLocale(): AppLocale {
  if (typeof window === "undefined") return DEFAULT_LOCALE;
  return localStorage.getItem(LOCALE_STORAGE_KEY) === "en" ? "en" : "vi";
}

let initPromise: Promise<void> | null = null;

export function ensureI18nReady(): Promise<void> {
  if (typeof window === "undefined") {
    return Promise.resolve();
  }

  if (initPromise) {
    return initPromise;
  }

  initPromise = (async () => {
    if (!i18n.isInitialized) {
      await i18n.use(initReactI18next).init({
        resources,
        lng: readStoredLocale(),
        fallbackLng: DEFAULT_LOCALE,
        supportedLngs: SUPPORTED_LOCALES,
        interpolation: { escapeValue: false },
        react: { useSuspense: false },
      });
      return;
    }

    const stored = readStoredLocale();
    if (i18n.language !== stored) {
      await i18n.changeLanguage(stored);
    }
  })();

  return initPromise;
}

export async function changeAppLocale(locale: AppLocale): Promise<void> {
  await ensureI18nReady();
  localStorage.setItem(LOCALE_STORAGE_KEY, locale);
  document.documentElement.lang = locale;
  await i18n.changeLanguage(locale);
}

export function normalizeLocale(language: string | undefined): AppLocale {
  return language?.startsWith("en") ? "en" : "vi";
}

export default i18n;
