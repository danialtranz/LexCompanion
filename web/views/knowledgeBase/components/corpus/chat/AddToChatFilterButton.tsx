"use client";

import { Filter } from "lucide-react";
import { useTranslation } from "react-i18next";
import { NODE_COLOR } from "../constants";

export function AddToChatFilterButton({
  nodeType,
  label,
  isAdded,
  onAdd,
  isDark,
}: {
  nodeType: "topic" | "subject";
  label: string;
  isAdded: boolean;
  onAdd: () => void;
  isDark?: boolean;
}) {
  const { t } = useTranslation();
  const color = nodeType === "topic" ? NODE_COLOR.topic : NODE_COLOR.subject;
  const typeLabel =
    nodeType === "topic" ? t("common.topic") : t("common.subject");

  if (isAdded) {
    return (
      <p
        className={`flex items-center gap-2 rounded-xl border px-4 py-2.5 text-sm font-medium ${
          isDark
            ? "border-slate-600 bg-slate-800/80 text-slate-300"
            : "border-slate-200 bg-slate-50 text-slate-600"
        }`}
        style={{ borderLeftWidth: 4, borderLeftColor: color }}
      >
        <Filter className="h-4 w-4 shrink-0 opacity-70" />
        {t("corpus.chat.alreadyInFilter")}
      </p>
    );
  }

  return (
    <button
      type="button"
      onClick={onAdd}
      className={`flex w-full items-center justify-center gap-2 rounded-xl border px-4 py-2.5 text-sm font-semibold shadow-sm transition hover:opacity-90 ${
        isDark ? "border-slate-600 text-white" : "text-white"
      }`}
      style={{
        backgroundColor: color,
        borderLeftWidth: 4,
        borderLeftColor: color,
      }}
      title={t("corpus.chat.addToFilterTitle", { type: typeLabel, label })}
    >
      <Filter className="h-4 w-4" />
      {t("corpus.chat.addToFilter")}
    </button>
  );
}
