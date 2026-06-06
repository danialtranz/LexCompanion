"use client";

import { Loader2, Send } from "lucide-react";
import type { KeyboardEvent } from "react";
import { useTranslation } from "react-i18next";

export function ChatInput({
  value,
  onChange,
  onSend,
  loading,
  disabled,
  isDark,
}: {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  loading: boolean;
  disabled?: boolean;
  isDark: boolean;
}) {
  const { t } = useTranslation();

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      onSend();
    }
  };

  return (
    <div
      className={`border-t px-3 py-3 ${
        isDark ? "border-slate-700 bg-slate-900/90" : "border-slate-100 bg-white"
      }`}
    >
      <div className="flex items-end gap-2">
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled || loading}
          rows={2}
          placeholder={t("corpus.chat.placeholder")}
          className={`min-h-[44px] flex-1 resize-none rounded-xl border px-3 py-2 text-sm outline-none transition focus:ring-2 focus:ring-emerald-500/30 ${
            isDark
              ? "border-slate-700 bg-slate-800 text-slate-100 placeholder:text-slate-500"
              : "border-slate-200 bg-slate-50 text-slate-900 placeholder:text-slate-400"
          }`}
        />
        <button
          type="button"
          onClick={onSend}
          disabled={disabled || loading || !value.trim()}
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-emerald-600 text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
          aria-label={t("common.send")}
        >
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
        </button>
      </div>
    </div>
  );
}
