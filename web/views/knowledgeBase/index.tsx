"use client";

import { useState } from "react";
import { UploadSource } from "./UploadSource";
import { FileTable } from "./FileTable";
import { UploadDocumentModal } from "./UploadDocumentModal";

export function KnowledgeBaseView() {
  const [modalOpen, setModalOpen] = useState(false);

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#faf8f5] text-stone-900">
      {/* Corner “light bulb” blurs */}
      <div
        className="pointer-events-none absolute -left-24 top-0 h-72 w-72 rounded-full bg-amber-200/40 blur-[100px]"
        aria-hidden
      />
      <div
        className="pointer-events-none absolute -right-20 top-24 h-80 w-80 rounded-full bg-violet-200/35 blur-[110px]"
        aria-hidden
      />
      <div
        className="pointer-events-none absolute bottom-0 left-1/4 h-64 w-64 rounded-full bg-sky-200/30 blur-[95px]"
        aria-hidden
      />
      <div
        className="pointer-events-none absolute -bottom-16 right-0 h-72 w-72 rounded-full bg-rose-200/25 blur-[100px]"
        aria-hidden
      />

      <div className="relative z-10 mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-10 lg:px-8 lg:py-12">
        <div className="flex flex-col gap-10 sm:gap-12 lg:gap-14">
          <UploadSource onOpenDocumentModal={() => setModalOpen(true)} />
          <FileTable />
        </div>
      </div>

      <UploadDocumentModal
        open={modalOpen}
        onOpenChange={setModalOpen}
      />
    </div>
  );
}
