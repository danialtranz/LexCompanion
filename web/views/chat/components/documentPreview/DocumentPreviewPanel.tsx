"use client";

import { FileText, Loader2, X } from "lucide-react";
import { PanelRight } from "../panelRight/PanelRight";
import type { ContractDraftVersionItem } from "@/hooks/useContractDraftVersions";
import { DocxBlobPreview } from "./DocxBlobPreview";
import { DraftVersionSidebar } from "./DraftVersionSidebar";
import { PlainTextDraftPreview } from "./PlainTextDraftPreview";
import { useTypewriterText } from "./useTypewriterText";

export type DocumentPreviewPanelProps = {
  plainText: string;
  onClose?: () => void;
  streaming?: boolean;
  chunkCurrent?: number;
  chunkTotal?: number;
  statusLabel?: string;
  liveMode?: boolean;
  /** DOCX binary từ MinIO — render trực tiếp bằng docx-preview. */
  previewBlob?: Blob | null;
  previewBlobLoading?: boolean;
  useMinioPreview?: boolean;
  versions?: ContractDraftVersionItem[];
  versionsLoading?: boolean;
  selectedVersion?: number | null;
  latestVersion?: number;
  onSelectVersion?: (version: number) => void;
  onDownloadVersion?: (version: number) => void;
  downloadingVersion?: number | null;
};

export const DocumentPreviewPanel = ({
  plainText,
  onClose,
  streaming = false,
  chunkCurrent,
  chunkTotal,
  statusLabel,
  liveMode = false,
  previewBlob = null,
  previewBlobLoading = false,
  useMinioPreview = false,
  versions = [],
  versionsLoading = false,
  selectedVersion = null,
  latestVersion,
  onSelectVersion,
  onDownloadVersion,
  downloadingVersion = null,
}: DocumentPreviewPanelProps) => {
  const showVersionBar = liveMode && Boolean(onSelectVersion);
  const displayedText = useTypewriterText(plainText, {
    enabled: streaming && !useMinioPreview,
    msPerChar: 8,
  });

  const useBlobPreview =
    useMinioPreview && (previewBlobLoading || Boolean(previewBlob?.size));

  const progress =
    chunkTotal != null && chunkTotal > 0 && chunkCurrent != null
      ? `Đoạn ${chunkCurrent + 1}/${chunkTotal}`
      : null;

  const fallbackPlaceholder = (() => {
    if (useMinioPreview && previewBlobLoading) {
      return "Đang tải văn bản…";
    }
    return "Chưa có nội dung bản nháp…";
  })();

  const documentBody = useBlobPreview ? (
    previewBlob?.size ? (
      <DocxBlobPreview
        blob={previewBlob}
        bare={liveMode}
        className="min-w-0 w-full"
      />
    ) : (
      <PlainTextDraftPreview
        text=""
        bare={liveMode}
        placeholder={fallbackPlaceholder}
        className="min-w-0 w-full"
      />
    )
  ) : (
    <PlainTextDraftPreview
      text={displayedText}
      bare={liveMode}
      placeholder={fallbackPlaceholder}
      className="min-w-0 w-full"
    />
  );

  const isLoadingPreview =
    (useMinioPreview && previewBlobLoading) || (!useMinioPreview && streaming);

  return (
    <PanelRight liveDocument={liveMode}>
      <div className="flex min-h-0 flex-1 flex-col">
        <div className="flex h-[60px] shrink-0 items-center gap-2.5 border-b border-[#ebe3d6] px-6">
          <FileText className="h-4 w-4 shrink-0 text-[#9a6c2b]" strokeWidth={2} />
          <div className="min-w-0 flex-1 overflow-hidden">
            <div className="flex min-w-0 items-center gap-2">
              <h2 className="m-0 shrink-0 text-sm font-semibold whitespace-nowrap text-[#2c2620]">
                Bản nháp văn bản
              </h2>
              {liveMode && (
                <span className="inline-flex items-center gap-1 rounded-full border border-[#b8e0c8] bg-[#edf8f1] px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-[#2d7a4a]">
                  <span className="relative flex h-1.5 w-1.5">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#3cb371] opacity-60" />
                    <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-[#3cb371]" />
                  </span>
                  Live
                </span>
              )}
            </div>
            {(liveMode && streaming) || progress || statusLabel ? (
              <p className="m-0 truncate text-xs text-[#8a8178]">
                {liveMode && streaming ? "AI đang chỉnh sửa" : null}
                {liveMode && streaming && (progress || statusLabel) ? " · " : null}
                {progress}
                {progress && statusLabel ? " · " : ""}
                {statusLabel}
              </p>
            ) : null}
          </div>
          {isLoadingPreview && (
            <Loader2
              className="h-4 w-4 shrink-0 animate-spin text-[#9a6c2b]"
              strokeWidth={2}
              aria-hidden
            />
          )}
          <div className="flex shrink-0 items-center gap-1">
            {onDownloadVersion && latestVersion != null && latestVersion > 0 ? (
              <button
                type="button"
                aria-label="Tải bản nháp DOCX mới nhất"
                onClick={() => onDownloadVersion(latestVersion)}
                className="cursor-pointer rounded-lg border border-[#ebe3d6] bg-white px-2.5 py-1.5 text-[11px] font-medium text-[#9a6c2b] transition-colors hover:bg-[#faf5ec]"
              >
                Tải DOCX
              </button>
            ) : null}
            {onClose ? (
              <button
                type="button"
                aria-label="Đóng panel bản nháp"
                onClick={onClose}
                className="grid h-8 w-8 shrink-0 cursor-pointer place-items-center rounded-lg border-0 bg-transparent text-[#8a8178] transition-colors hover:bg-[#faf5ec] hover:text-[#2c2620]"
              >
                <X className="h-4 w-4" strokeWidth={2} />
              </button>
            ) : null}
          </div>
        </div>

        {showVersionBar ? (
          <DraftVersionSidebar
            versions={versions}
            selectedVersion={selectedVersion}
            latestVersion={latestVersion}
            loading={versionsLoading}
            onSelectVersion={onSelectVersion!}
            onDownloadVersion={onDownloadVersion}
            downloadingVersion={downloadingVersion}
          />
        ) : null}

        <div
          className={`flex min-h-0 flex-1 flex-col overflow-hidden ${
            liveMode ? "bg-[#ece8e1]" : "bg-white"
          }`}
        >
          <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5 lg:px-8 lg:py-6">
            {liveMode ? (
              <div className="mx-auto w-full max-w-[860px] rounded-sm border border-[#e0dbd2] bg-white px-8 py-10 shadow-[0_4px_24px_rgba(44,38,32,0.08)] min-[1400px]:max-w-[920px]">
                {documentBody}
              </div>
            ) : (
              <div className="flex min-h-0 min-w-0 flex-1 flex-col">{documentBody}</div>
            )}
          </div>
        </div>
      </div>
    </PanelRight>
  );
};
