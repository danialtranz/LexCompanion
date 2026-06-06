"use client";

import { useTranslation } from "react-i18next";
import { NODE_COLOR, SELECTED_TOPIC_COLOR } from "../constants";

export function LegendCard({ isDark }: { isDark: boolean }) {
  const { t } = useTranslation();
  const items = [
    { label: t("common.topic"), color: NODE_COLOR.topic },
    { label: t("common.subject"), color: NODE_COLOR.subject },
    { label: t("corpus.legend.article"), color: NODE_COLOR.article },
    { label: t("common.selected"), color: SELECTED_TOPIC_COLOR, ring: true },
  ];

  return (
    <div
      className={`pointer-events-none absolute bottom-4 left-4 z-10 rounded-2xl border px-4 py-3 shadow-lg backdrop-blur-sm ${
        isDark
          ? "border-slate-700/80 bg-slate-900/85"
          : "border-white/80 bg-white/90"
      }`}
    >
      <p
        className={`mb-2.5 text-[10px] font-bold uppercase tracking-widest ${
          isDark ? "text-slate-400" : "text-slate-500"
        }`}
      >
        {t("corpus.legend.title")}
      </p>
      <div className="space-y-2">
        {items.map((item) => (
          <div key={item.label} className="flex items-center gap-2.5">
            <span
              className={`h-3 w-3 shrink-0 rounded-full ${item.ring ? "ring-2 ring-offset-1" : ""}`}
              style={{
                backgroundColor: item.color,
                ...(item.ring
                  ? {
                      boxShadow: `0 0 0 2px ${item.color}55`,
                      ringColor: item.color,
                    }
                  : {}),
              }}
            />
            <span
              className={`text-xs font-medium ${isDark ? "text-slate-300" : "text-slate-600"}`}
            >
              {item.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
