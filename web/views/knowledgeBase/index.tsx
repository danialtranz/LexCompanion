"use client";

import { useCallback, useRef, useState } from "react";
import { useRouter } from "next/router";
import { useTranslation } from "react-i18next";
import { ChatLayout } from "../chat/components/layout/ChatLayout";
import { ChatMain } from "../chat/components/layout/ChatMain";
import { UploadSource } from "./UploadSource";
import { FileTable } from "./FileTable";
import { UploadDocumentModal } from "./UploadDocumentModal";
import { LegalCorpusVisualize } from "./LegalCorpusVisualize";
import { useIsAdminUser } from "../../hooks/useIsAdminUser";

type KnowledgeView = "files" | "visualize";

export function KnowledgeBaseView() {
  const { t } = useTranslation();
  const router = useRouter();
  const [modalOpen, setModalOpen] = useState(false);
  const [activeView, setActiveView] = useState<KnowledgeView>("files");
  const isAdmin = useIsAdminUser();
  const refetchFilesRef = useRef<(() => void) | null>(null);

  const handleRefetchReady = useCallback((refetch: () => void) => {
    refetchFilesRef.current = refetch;
  }, []);

  const goToChat = useCallback(() => {
    void router.push("/chat");
  }, [router]);

  return (
    <ChatLayout
      onCreateConversation={goToChat}
      onOpenKnowledgeBase={goToChat}
      onToggleHistory={goToChat}
    >
      <ChatMain>
        <div className="relative min-h-0 flex-1 overflow-y-auto overflow-x-hidden bg-[#faf8f5] text-stone-900">
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

              <section className="w-full">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex flex-wrap items-center gap-3">
                    <h2 className="text-xl font-bold tracking-tight text-stone-900 sm:text-2xl">
                      {t("knowledgeBase.uploaded")}
                    </h2>
                    {isAdmin && (
                      <div
                        className="inline-flex rounded-xl border border-stone-200/90 bg-white/90 p-1 shadow-sm"
                        role="tablist"
                        aria-label={t("knowledgeBase.viewModeAria")}
                      >
                        <button
                          type="button"
                          role="tab"
                          aria-selected={activeView === "files"}
                          onClick={() => setActiveView("files")}
                          className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition sm:text-sm ${
                            activeView === "files"
                              ? "bg-violet-600 text-white shadow-sm"
                              : "text-stone-600 hover:bg-stone-50"
                          }`}
                        >
                          {t("knowledgeBase.tabDocuments")}
                        </button>
                        <button
                          type="button"
                          role="tab"
                          aria-selected={activeView === "visualize"}
                          onClick={() => setActiveView("visualize")}
                          className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition sm:text-sm ${
                            activeView === "visualize"
                              ? "bg-violet-600 text-white shadow-sm"
                              : "text-stone-600 hover:bg-stone-50"
                          }`}
                        >
                          {t("knowledgeBase.tabVisualize")}
                        </button>
                      </div>
                    )}
                  </div>
                  {activeView === "files" && (
                    <button
                      type="button"
                      onClick={() => refetchFilesRef.current?.()}
                      className="self-start text-sm font-medium text-violet-700 hover:underline sm:self-auto"
                    >
                      {t("common.refresh")}
                    </button>
                  )}
                </div>

                <div className="mt-4">
                  {activeView === "files" || !isAdmin ? (
                    <FileTable hideHeader onRefetchReady={handleRefetchReady} />
                  ) : (
                    <LegalCorpusVisualize />
                  )}
                </div>
              </section>
            </div>
          </div>

          <UploadDocumentModal open={modalOpen} onOpenChange={setModalOpen} />
        </div>
      </ChatMain>
    </ChatLayout>
  );
}
