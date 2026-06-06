"use client";

import { FormEvent, useMemo, useState } from "react";
import { FileText, Link2, Mic, Video } from "lucide-react";
import toast from "react-hot-toast";
import { useTranslation } from "react-i18next";
import { useUploadDocumentViaUrl } from "@/hooks/useDocumentHook";

type UploadSourceProps = {
  onOpenDocumentModal: () => void;
  kb_id?: string | null;
};

const cardConfigs = [
  {
    id: "documents" as const,
    icon: FileText,
    iconWrap: "from-violet-500 to-purple-600",
    glow: "bg-violet-400/35",
    ring: "ring-violet-200/80",
  },
  {
    id: "social" as const,
    icon: Link2,
    iconWrap: "from-emerald-500 to-teal-600",
    glow: "bg-emerald-400/35",
    ring: "ring-emerald-200/80",
  },
  {
    id: "audio" as const,
    icon: Mic,
    iconWrap: "from-sky-500 to-blue-600",
    glow: "bg-sky-400/35",
    ring: "ring-sky-200/80",
  },
  {
    id: "video" as const,
    icon: Video,
    iconWrap: "from-orange-500 to-rose-600",
    glow: "bg-orange-400/35",
    ring: "ring-orange-200/80",
  },
];

function isUploadOk(code: number) {
  return code === 201 || code === 0;
}

function isSnakeCase(raw: string): boolean {
  return /^[a-z0-9]+(?:_[a-z0-9]+)*$/.test(raw);
}

async function probeUrlReachable(url: string): Promise<boolean> {
  const ctl = new AbortController();
  const timeout = window.setTimeout(() => ctl.abort(), 4000);
  try {
    await fetch(url, {
      method: "HEAD",
      mode: "no-cors",
      cache: "no-store",
      redirect: "follow",
      signal: ctl.signal,
    });
    return true;
  } catch {
    return false;
  } finally {
    window.clearTimeout(timeout);
  }
}

export function UploadSource({ onOpenDocumentModal, kb_id = null }: UploadSourceProps) {
  const { t } = useTranslation();
  const [urlModalOpen, setUrlModalOpen] = useState(false);
  const [urlValue, setUrlValue] = useState("");
  const [docName, setDocName] = useState("");
  const { uploadDocumentViaUrl, loading } = useUploadDocumentViaUrl();

  const cardLabels = {
    documents: t("knowledgeBase.upload.cardDocuments"),
    social: t("knowledgeBase.upload.cardSocial"),
    audio: t("knowledgeBase.upload.cardAudio"),
    video: t("knowledgeBase.upload.cardVideo"),
  };

  const submitDisabled = useMemo(
    () => !urlValue.trim() || !docName.trim() || loading,
    [urlValue, docName, loading],
  );

  const onSubmitUrl = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const url = urlValue.trim();
    const name = docName.trim();
    if (!url) {
      toast.error(t("knowledgeBase.upload.urlEmpty"));
      return;
    }
    if (!name) {
      toast.error(t("knowledgeBase.upload.nameEmpty"));
      return;
    }
    if (!isSnakeCase(name)) {
      toast.error(t("knowledgeBase.upload.nameSnakeCase"));
      return;
    }

    try {
      new URL(url);
    } catch {
      toast.error(t("knowledgeBase.upload.urlInvalid"));
      return;
    }

    const reachable = await probeUrlReachable(url);
    if (!reachable) {
      toast.error(t("knowledgeBase.upload.urlUnreachable"));
      return;
    }

    try {
      const res = await toast.promise(
        uploadDocumentViaUrl({
          url,
          doc_name: name,
          kb_id,
        }),
        {
          loading: t("knowledgeBase.upload.uploadingFromUrl"),
          success: t("knowledgeBase.upload.uploadFromUrlSuccess"),
          error: t("knowledgeBase.upload.uploadFromUrlFailed"),
        },
      );
      if (!isUploadOk(res.code)) {
        toast.error(res.msg || t("knowledgeBase.upload.uploadFromUrlFailed"));
        return;
      }
      setUrlModalOpen(false);
      setUrlValue("");
      setDocName("");
    } catch {
      // handled by toast.promise
    }
  };

  return (
    <section className="w-full">
      <h1 className="text-2xl font-bold tracking-tight text-stone-900 sm:text-3xl">
        {t("knowledgeBase.addKnowledge")}
      </h1>
      <p className="mt-2 max-w-3xl text-sm leading-relaxed text-stone-600 sm:text-base">
        {t("knowledgeBase.addKnowledgeDescription")}
      </p>

      <div className="mt-8 grid grid-cols-2 gap-3 sm:grid-cols-2 sm:gap-4 lg:grid-cols-4">
        {cardConfigs.map((card) => {
          const Icon = card.icon;
          const isDocs = card.id === "documents";
          return (
            <button
              key={card.id}
              type="button"
              onClick={() => {
                if (isDocs) {
                  onOpenDocumentModal();
                } else if (card.id === "social") {
                  setUrlModalOpen(true);
                } else {
                  toast(t("knowledgeBase.upload.unsupported"));
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
                {cardLabels[card.id]}
              </span>
            </button>
          );
        })}
      </div>

      {urlModalOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6"
          role="dialog"
          aria-modal="true"
          aria-labelledby="upload-url-title"
        >
          <button
            type="button"
            className="absolute inset-0 z-0 bg-stone-900/25 backdrop-blur-sm transition-opacity"
            aria-label={t("common.close")}
            onClick={() => !loading && setUrlModalOpen(false)}
          />
          <div className="relative z-10 w-full max-w-lg">
            <div className="overflow-hidden rounded-2xl border border-stone-200/80 bg-[#fefdfb] shadow-2xl shadow-stone-300/40 ring-1 ring-white/80">
              <div className="border-b border-stone-100 px-5 py-4 sm:px-6">
                <h2
                  id="upload-url-title"
                  className="text-lg font-semibold tracking-tight text-stone-900"
                >
                  {t("knowledgeBase.upload.urlModalTitle")}
                </h2>
                <p className="mt-1 text-sm text-stone-500">
                  {t("knowledgeBase.upload.urlModalDescription")}
                </p>
              </div>
              <form className="space-y-4 p-5 sm:p-6" onSubmit={onSubmitUrl}>
                <div>
                  <label
                    htmlFor="upload-url-input"
                    className="mb-1.5 block text-sm font-medium text-stone-700"
                  >
                    {t("common.url")}
                  </label>
                  <input
                    id="upload-url-input"
                    type="url"
                    value={urlValue}
                    onChange={(e) => setUrlValue(e.target.value)}
                    placeholder="https://example.com/article"
                    disabled={loading}
                    required
                    className="w-full rounded-xl border border-stone-200 bg-white px-3 py-2.5 text-sm text-stone-900 outline-none transition focus:border-violet-400 focus:ring-2 focus:ring-violet-200"
                  />
                </div>
                <div>
                  <label
                    htmlFor="upload-doc-name-input"
                    className="mb-1.5 block text-sm font-medium text-stone-700"
                  >
                    {t("knowledgeBase.upload.documentName")}
                  </label>
                  <input
                    id="upload-doc-name-input"
                    type="text"
                    value={docName}
                    onChange={(e) => setDocName(e.target.value)}
                    placeholder={t("knowledgeBase.upload.documentNamePlaceholder")}
                    disabled={loading}
                    required
                    className="w-full rounded-xl border border-stone-200 bg-white px-3 py-2.5 text-sm text-stone-900 outline-none transition focus:border-violet-400 focus:ring-2 focus:ring-violet-200"
                  />
                  <p className="mt-1 text-xs text-stone-500">
                    {t("knowledgeBase.upload.documentNameHint")}
                  </p>
                </div>
                <div className="flex justify-end gap-2 pt-2">
                  <button
                    type="button"
                    disabled={loading}
                    onClick={() => setUrlModalOpen(false)}
                    className="rounded-xl border border-stone-200 bg-white px-4 py-2 text-sm font-medium text-stone-700 transition hover:bg-stone-50 disabled:opacity-60"
                  >
                    {t("common.cancel")}
                  </button>
                  <button
                    type="submit"
                    disabled={submitDisabled}
                    className="rounded-xl bg-gradient-to-r from-violet-600 to-fuchsia-600 px-4 py-2 text-sm font-semibold text-white shadow-md transition hover:from-violet-500 hover:to-fuchsia-500 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {loading ? t("knowledgeBase.upload.uploading") : t("common.upload")}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
