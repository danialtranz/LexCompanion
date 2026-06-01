"use client";

import { X } from "lucide-react";
import { NODE_COLOR } from "../constants";
import type { ChatReferenceItem } from "./types";

function ReferenceChip({
  item,
  onRemove,
  isDark,
}: {
  item: ChatReferenceItem;
  onRemove: () => void;
  isDark: boolean;
}) {
  const color =
    item.nodeType === "topic" ? NODE_COLOR.topic : NODE_COLOR.subject;
  const typeLabel = item.nodeType === "topic" ? "Topic" : "Subject";

  return (
    <span
      className={`inline-flex max-w-full items-center gap-1.5 rounded-lg border px-2 py-1 text-xs font-medium ${
        isDark
          ? "border-slate-600 bg-slate-800 text-slate-100"
          : "border-slate-200 bg-white text-slate-800"
      }`}
      style={{ borderLeftWidth: 3, borderLeftColor: color }}
    >
      <span
        className={`shrink-0 text-[10px] font-bold uppercase tracking-wide ${
          isDark ? "text-slate-400" : "text-slate-500"
        }`}
      >
        {typeLabel}
      </span>
      <span className="min-w-0 truncate">{item.label}</span>
      <button
        type="button"
        onClick={onRemove}
        className={`shrink-0 rounded p-0.5 transition ${
          isDark
            ? "text-slate-400 hover:bg-slate-700 hover:text-slate-200"
            : "text-slate-400 hover:bg-slate-100 hover:text-slate-700"
        }`}
        aria-label={`Xóa ${typeLabel} ${item.label}`}
      >
        <X className="h-3 w-3" />
      </button>
    </span>
  );
}

export function ChatReferenceChips({
  topics,
  subjects,
  onRemoveTopic,
  onRemoveSubject,
  onClearAll,
  isDark,
}: {
  topics: ChatReferenceItem[];
  subjects: ChatReferenceItem[];
  onRemoveTopic: (id: string) => void;
  onRemoveSubject: (id: string) => void;
  onClearAll: () => void;
  isDark: boolean;
}) {
  if (topics.length === 0 && subjects.length === 0) {
    return (
      <p
        className={`text-[11px] leading-relaxed ${
          isDark ? "text-slate-500" : "text-slate-400"
        }`}
      >
        Giữ & kéo node Topic/Subject từ đồ thị vào đây, hoặc bấm &quot;Thêm vào
        bộ lọc&quot; ở panel chi tiết.
      </p>
    );
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-1.5">
        {topics.map((item) => (
          <ReferenceChip
            key={`topic-${item.id}`}
            item={item}
            onRemove={() => onRemoveTopic(item.id)}
            isDark={isDark}
          />
        ))}
        {subjects.map((item) => (
          <ReferenceChip
            key={`subject-${item.id}`}
            item={item}
            onRemove={() => onRemoveSubject(item.id)}
            isDark={isDark}
          />
        ))}
      </div>
      <button
        type="button"
        onClick={onClearAll}
        className={`text-[11px] font-semibold underline-offset-2 hover:underline ${
          isDark ? "text-slate-400 hover:text-slate-200" : "text-slate-500 hover:text-slate-700"
        }`}
      >
        Xóa tất cả bộ lọc
      </button>
    </div>
  );
}
