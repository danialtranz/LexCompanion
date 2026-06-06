"use client";

import { Check, Download, Loader2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import type { ContractDraftVersionItem } from "@/hooks/useContractDraftVersions";
import { formatHistoryTimestamp } from "../../utils/formatHistoryTimestamp";

export type DraftVersionSidebarProps = {
  versions: ContractDraftVersionItem[];
  selectedVersion: number | null;
  latestVersion?: number;
  loading?: boolean;
  onSelectVersion: (version: number) => void;
  onDownloadVersion?: (version: number) => void;
  downloadingVersion?: number | null;
};

function formatVersionTime(createdAt?: string): string {
  return formatHistoryTimestamp(createdAt);
}

function versionStatusLabel(
  item: ContractDraftVersionItem,
  isLatest: boolean,
  t: (key: string) => string,
): string {
  if (isLatest) return t("chat.draft.versionLatest");
  if (item.version === 0) return t("chat.draft.versionInit");
  return t("chat.draft.versionAiEdit");
}

export const DraftVersionSidebar = ({
  versions,
  selectedVersion,
  latestVersion,
  loading = false,
  onSelectVersion,
  onDownloadVersion,
  downloadingVersion = null,
}: DraftVersionSidebarProps) => {
  const { t } = useTranslation();
  const effectiveSelected =
    selectedVersion ?? latestVersion ?? versions[versions.length - 1]?.version;

  const ordered = [...versions].reverse();

  return (
    <section className="shrink-0 border-b border-[#ebe3d6] bg-[#faf7f2] px-5 py-3">
      <div className="mb-2.5 flex items-center justify-between gap-3">
        <div>
          <h3 className="m-0 text-xs font-semibold text-[#2c2620]">
            {t("chat.draft.versionHistory")}
          </h3>
          <p className="m-0 mt-0.5 text-[10px] text-[#8a8178]">
            {t("chat.draft.versionHistoryHint")}
          </p>
        </div>
        {ordered.length > 4 ? (
          <span className="shrink-0 text-[10px] font-medium text-[#9a6c2b]">
            {t("chat.draft.viewAllVersions", { count: ordered.length })}
          </span>
        ) : null}
      </div>

      {loading && versions.length === 0 ? (
        <div className="flex items-center gap-2 py-3 text-xs text-[#8a8178]">
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          {t("chat.draft.loadingVersions")}
        </div>
      ) : null}

      {!loading && versions.length === 0 ? (
        <p className="m-0 py-2 text-[11px] text-[#a89f96]">
          {t("chat.draft.noSavedVersions")}
        </p>
      ) : null}

      {ordered.length > 0 ? (
        <div className="flex gap-2 overflow-x-auto pb-1 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
          {ordered.map((item) => {
            const isSelected = item.version === effectiveSelected;
            const isLatest =
              item.is_latest ?? item.version === latestVersion;
            const timeLabel = formatVersionTime(item.created_at);
            const status = versionStatusLabel(item, isLatest, t);

            return (
              <button
                key={item.version}
                type="button"
                onClick={() => onSelectVersion(item.version)}
                className={`flex min-w-[148px] shrink-0 cursor-pointer flex-col rounded-xl border px-3 py-2.5 text-left transition-colors ${
                  isSelected
                    ? "border-[#b8e0c8] bg-[#edf8f1] shadow-sm"
                    : "border-[#ebe3d6] bg-white hover:border-[#d4cfc6] hover:bg-[#fffdf9]"
                }`}
              >
                <span className="flex items-center gap-1.5 text-xs font-semibold text-[#2c2620]">
                  {isSelected ? (
                    <Check
                      className="h-3 w-3 shrink-0 text-[#2d7a4a]"
                      strokeWidth={2.5}
                    />
                  ) : (
                    <span className="inline-block h-3 w-3 shrink-0 rounded-full border border-[#d4cfc6]" />
                  )}
                  {t("chat.draft.versionLabel", { version: item.version })}
                  {isLatest ? (
                    <span className="rounded bg-[#2d7a4a]/10 px-1 py-0.5 text-[9px] font-bold uppercase text-[#2d7a4a]">
                      {t("chat.draft.versionNew")}
                    </span>
                  ) : null}
                </span>
                {timeLabel ? (
                  <span className="mt-1 pl-[18px] text-[10px] text-[#8a8178]">
                    {timeLabel}
                  </span>
                ) : null}
                <span className="mt-0.5 pl-[18px] text-[10px] text-[#a89f96]">
                  {status}
                </span>
                {onDownloadVersion ? (
                  <span
                    role="button"
                    tabIndex={0}
                    aria-label={t("chat.draft.downloadVersion", {
                      version: item.version,
                    })}
                    onClick={(e) => {
                      e.stopPropagation();
                      onDownloadVersion(item.version);
                    }}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        e.stopPropagation();
                        onDownloadVersion(item.version);
                      }
                    }}
                    className="mt-1.5 ml-[18px] inline-flex w-fit cursor-pointer items-center gap-1 text-[10px] text-[#9a6c2b] hover:underline"
                  >
                    {downloadingVersion === item.version ? (
                      <Loader2 className="h-3 w-3 animate-spin" />
                    ) : (
                      <Download className="h-3 w-3" />
                    )}
                    {t("chat.draft.downloadDocx")}
                  </span>
                ) : null}
              </button>
            );
          })}
        </div>
      ) : null}
    </section>
  );
};
