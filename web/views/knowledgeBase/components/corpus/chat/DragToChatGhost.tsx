"use client";

import { useTranslation } from "react-i18next";
import { NODE_COLOR } from "../constants";
import type { ChatReferenceItem } from "./types";

export function DragToChatGhost({
  item,
  x,
  y,
}: {
  item: ChatReferenceItem;
  x: number;
  y: number;
}) {
  const { t } = useTranslation();
  const color =
    item.nodeType === "topic" ? NODE_COLOR.topic : NODE_COLOR.subject;
  const typeLabel =
    item.nodeType === "topic" ? t("common.topic") : t("common.subject");

  return (
    <div
      className="pointer-events-none fixed z-[9999] flex max-w-[220px] items-center gap-2 rounded-xl border border-slate-200 bg-white/95 px-3 py-2 text-xs font-semibold text-slate-800 shadow-xl backdrop-blur-sm"
      style={{
        left: x + 12,
        top: y + 12,
        borderLeftWidth: 4,
        borderLeftColor: color,
      }}
    >
      <span className="text-[10px] uppercase tracking-wide text-slate-500">
        {typeLabel}
      </span>
      <span className="truncate">{item.label}</span>
    </div>
  );
}
