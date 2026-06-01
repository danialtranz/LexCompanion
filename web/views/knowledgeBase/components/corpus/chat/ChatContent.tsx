"use client";

import { Loader2 } from "lucide-react";
import type { ChatMessage } from "./types";

export function ChatContent({
  messages,
  loading,
  isDark,
}: {
  messages: ChatMessage[];
  loading: boolean;
  isDark: boolean;
}) {
  if (messages.length === 0 && !loading) {
    return (
      <div
        className={`flex flex-1 flex-col items-center justify-center px-4 py-8 text-center text-sm ${
          isDark ? "text-slate-400" : "text-slate-500"
        }`}
      >
        <p className="font-medium">Hỏi về nội dung pháp điển</p>
        <p className="mt-1 text-xs opacity-80">
          Câu trả lời kèm trích dẫn [1], [2]… và danh sách nguồn bên dưới.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col gap-4 overflow-y-auto px-4 py-3">
      {messages.map((msg) => (
        <div
          key={msg.id}
          className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
        >
          <div
            className={`max-w-[95%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed ${
              msg.role === "user"
                ? "bg-emerald-600 text-white"
                : msg.error
                  ? isDark
                    ? "border border-rose-500/40 bg-rose-950/40 text-rose-200"
                    : "border border-rose-200 bg-rose-50 text-rose-800"
                  : isDark
                    ? "border border-slate-700 bg-slate-800 text-slate-100"
                    : "border border-slate-200 bg-slate-50 text-slate-800"
            }`}
          >
            <p className="whitespace-pre-wrap">{msg.content}</p>
            {msg.role === "assistant" &&
              msg.references &&
              msg.references.length > 0 && (
                <ul
                  className={`mt-3 space-y-1.5 border-t pt-2 text-xs ${
                    isDark ? "border-slate-600 text-slate-300" : "border-slate-200 text-slate-600"
                  }`}
                >
                  {msg.references.map((ref) => (
                    <li key={`${msg.id}-ref-${ref.index}`}>
                      <span className="font-medium">[{ref.index}]</span>{" "}
                      {ref.ieee?.replace(/^\[\d+\]\s*/, "") ?? ref.article_title}
                    </li>
                  ))}
                </ul>
              )}
          </div>
        </div>
      ))}
      {loading && (
        <div className="flex items-center gap-2 text-sm text-emerald-600">
          <Loader2 className="h-4 w-4 animate-spin" />
          Đang tra cứu và tổng hợp câu trả lời…
        </div>
      )}
    </div>
  );
}
