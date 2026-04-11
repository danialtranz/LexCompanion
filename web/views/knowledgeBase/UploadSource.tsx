"use client";

import { FileText, Link2, Mic, Video } from "lucide-react";
import toast from "react-hot-toast";

const UNSUPPORTED_MSG =
  "Tính năng này tạm thời chưa được hỗ trợ. Hiện chỉ có thể tải tài liệu.";

type UploadSourceProps = {
  onOpenDocumentModal: () => void;
};

const cards = [
  {
    id: "documents" as const,
    label: "Documents",
    icon: FileText,
    iconWrap: "from-violet-500 to-purple-600",
    glow: "bg-violet-400/35",
    ring: "ring-violet-200/80",
  },
  {
    id: "social" as const,
    label: "Social link",
    icon: Link2,
    iconWrap: "from-emerald-500 to-teal-600",
    glow: "bg-emerald-400/35",
    ring: "ring-emerald-200/80",
  },
  {
    id: "audio" as const,
    label: "Upload audio",
    icon: Mic,
    iconWrap: "from-sky-500 to-blue-600",
    glow: "bg-sky-400/35",
    ring: "ring-sky-200/80",
  },
  {
    id: "video" as const,
    label: "Upload video",
    icon: Video,
    iconWrap: "from-orange-500 to-rose-600",
    glow: "bg-orange-400/35",
    ring: "ring-orange-200/80",
  },
];

export function UploadSource({ onOpenDocumentModal }: UploadSourceProps) {
  return (
    <section className="w-full">
      <h1 className="text-2xl font-bold tracking-tight text-stone-900 sm:text-3xl">
        Add knowledge
      </h1>
      <p className="mt-2 max-w-3xl text-sm leading-relaxed text-stone-600 sm:text-base">
        Please upload a file to load knowledge into the agent and personalize
        your interactive experience!
      </p>

      <div className="mt-8 grid grid-cols-2 gap-3 sm:grid-cols-2 sm:gap-4 lg:grid-cols-4">
        {cards.map((card) => {
          const Icon = card.icon;
          const isDocs = card.id === "documents";
          return (
            <button
              key={card.id}
              type="button"
              onClick={() => {
                if (isDocs) {
                  onOpenDocumentModal();
                } else {
                  toast(UNSUPPORTED_MSG);
                }
              }}
              className="group relative flex flex-col items-center overflow-hidden rounded-2xl border border-stone-200/90 bg-white/70 p-5 text-center shadow-sm ring-1 ring-stone-100/80 transition hover:-translate-y-0.5 hover:border-stone-300 hover:shadow-md focus:outline-none focus-visible:ring-2 focus-visible:ring-violet-400 focus-visible:ring-offset-2"
            >
              <div
                className={`pointer-events-none absolute inset-0 opacity-0 transition group-hover:opacity-100`}
                aria-hidden
              >
                <div
                  className={`absolute -top-8 left-1/2 h-32 w-32 -translate-x-1/2 rounded-full ${card.glow} blur-2xl`}
                />
              </div>
              <div className="relative mb-4 flex h-[72px] w-[72px] items-center justify-center">
                <div
                  className={`absolute h-16 w-16 rounded-2xl ${card.glow} blur-xl`}
                  aria-hidden
                />
                <div
                  className={`relative flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br ${card.iconWrap} text-white shadow-lg ring-2 ${card.ring}`}
                >
                  <Icon className="h-7 w-7" strokeWidth={1.75} />
                </div>
              </div>
              <span className="relative text-sm font-semibold text-stone-800">
                {card.label}
              </span>
            </button>
          );
        })}
      </div>
    </section>
  );
}
