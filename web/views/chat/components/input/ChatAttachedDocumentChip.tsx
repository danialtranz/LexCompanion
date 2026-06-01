"use client";

import { FileText, Image as ImageIcon, X } from "lucide-react";
import type { ChatAttachedDocument } from "@/views/chat/utils/chatDocumentDrag";

type ChatAttachedDocumentChipProps = {
  doc: ChatAttachedDocument;
  onRemove: () => void;
  disabled?: boolean;
};

function ChipIcon({ type }: { type: string }) {
  const t = type.toLowerCase();
  if (/\b(png|jpe?g|gif|webp)\b/.test(t)) {
    return (
      <div className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-[#f0f5ec] text-[#6b8f4e]">
        <ImageIcon className="h-[18px] w-[18px]" strokeWidth={2} />
      </div>
    );
  }
  if (t.includes("pdf")) {
    return (
      <div className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-[#fdf0ed] text-[#c45c4a]">
        <FileText className="h-[18px] w-[18px]" strokeWidth={2} />
      </div>
    );
  }
  return (
    <div className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-[#eef4fc] text-[#4a7fc1]">
      <FileText className="h-[18px] w-[18px]" strokeWidth={2} />
    </div>
  );
}

export const ChatAttachedDocumentChip = ({
  doc,
  onRemove,
  disabled = false,
}: ChatAttachedDocumentChipProps) => (
  <div className="relative flex min-w-[148px] max-w-[240px] items-center gap-2.5 rounded-xl border border-[#ebe3d6] bg-[#faf7f2] py-2 pl-2.5 pr-9">
    <ChipIcon type={doc.type} />
    <div className="min-w-0 flex-1">
      <p className="m-0 truncate text-sm font-medium leading-tight text-[#2c2620]">
        {doc.name}
      </p>
      <p className="mt-0.5 m-0 text-[11px] font-semibold uppercase tracking-wide text-[#8a8178]">
        {doc.type}
      </p>
    </div>
    <button
      type="button"
      disabled={disabled}
      aria-label={`Gỡ ${doc.name} khỏi tin nhắn`}
      onClick={onRemove}
      className="absolute right-1.5 top-1.5 grid h-6 w-6 place-items-center rounded-full border-0 bg-[#f5efe4] text-[#8a8178] transition-colors hover:bg-[#ebe3d6] hover:text-[#2c2620] disabled:opacity-40 cursor-pointer"
    >
      <X className="h-3.5 w-3.5" strokeWidth={2.5} />
    </button>
  </div>
);
