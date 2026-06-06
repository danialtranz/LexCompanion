"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { FolderOpen, HardDriveUpload, Loader2, Paperclip } from "lucide-react";
import toast from "react-hot-toast";
import { useTranslation } from "react-i18next";
import {
  useUploadUserDocument,
  type UploadUserDocumentData,
} from "@/hooks/useDocumentHook";

const ACCEPT = ".pdf,.docx,.jpg,.jpeg,.png";
const MAX_BYTES = 50 * 1024 * 1024;

type ChatAttachDropupProps = {
  disabled?: boolean;
  sessionId?: string | null;
  onOpenKnowledgeBase?: () => void;
  onUploadSuccess?: (data: UploadUserDocumentData) => void;
};

function isUploadOk(code: number) {
  return code === 201 || code === 0;
}

export const ChatAttachDropup = ({
  disabled = false,
  sessionId = null,
  onOpenKnowledgeBase,
  onUploadSuccess,
}: ChatAttachDropupProps) => {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { upload, loading: uploading } = useUploadUserDocument();

  const isDisabled = disabled || uploading;

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  const handleFiles = useCallback(
    async (fileList: FileList | null) => {
      if (!fileList?.length || isDisabled) return;
      setOpen(false);
      if (fileInputRef.current) fileInputRef.current.value = "";

      for (const file of Array.from(fileList)) {
        if (file.size > MAX_BYTES) {
          toast.error(t("chat.input.fileTooLarge", { name: file.name }));
          continue;
        }
        try {
          const res = await upload({ file, session_id: sessionId });
          if (!isUploadOk(res.code) || !res.data) {
            toast.error(res.msg || t("chat.input.uploadFailed"));
            continue;
          }
          onUploadSuccess?.(res.data);
          toast.success(
            t("chat.input.uploadSuccess", { name: res.data.name }),
          );
        } catch (err) {
          const msg =
            err instanceof Error ? err.message : t("chat.input.uploadFailed");
          toast.error(msg);
        }
      }
    },
    [isDisabled, onUploadSuccess, sessionId, upload, t],
  );

  const openFilePicker = () => {
    if (isDisabled) return;
    setOpen(false);
    fileInputRef.current?.click();
  };

  const openMyDocuments = () => {
    if (isDisabled) return;
    setOpen(false);
    onOpenKnowledgeBase?.();
  };

  return (
    <div ref={rootRef} className="relative shrink-0">
      <input
        ref={fileInputRef}
        type="file"
        accept={ACCEPT}
        multiple
        className="hidden"
        disabled={isDisabled}
        onChange={(e) => void handleFiles(e.target.files)}
      />

      <button
        type="button"
        aria-label={t("chat.input.attachDocument")}
        aria-expanded={open}
        aria-haspopup="menu"
        disabled={isDisabled}
        onClick={() => setOpen((v) => !v)}
        className="grid h-9 w-9 place-items-center rounded-lg border-0 bg-transparent text-[#8a8178] transition-colors hover:bg-[#faf5ec] hover:text-[#9a6c2b] cursor-pointer disabled:cursor-not-allowed disabled:opacity-50"
      >
        {uploading ? (
          <Loader2 className="h-[18px] w-[18px] animate-spin" strokeWidth={2} />
        ) : (
          <Paperclip className="h-[18px] w-[18px]" strokeWidth={2} />
        )}
      </button>

      {open && (
        <div
          role="menu"
          className="absolute bottom-full right-0 z-[100] mb-2 min-w-[220px] overflow-hidden rounded-xl border border-[#ebe3d6] bg-white py-1 shadow-[0_8px_28px_rgba(84,59,28,0.12)]"
        >
          <button
            type="button"
            role="menuitem"
            onClick={openFilePicker}
            className="flex w-full items-center gap-3 border-0 bg-transparent px-3.5 py-2.5 text-left text-sm text-[#2c2620] transition-colors hover:bg-[#faf5ec] cursor-pointer"
          >
            <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-[#f5e6cc] text-[#9a6c2b]">
              <HardDriveUpload className="h-4 w-4" strokeWidth={2} />
            </span>
            <span className="font-medium">{t("chat.input.uploadFromComputer")}</span>
          </button>
          <button
            type="button"
            role="menuitem"
            onClick={openMyDocuments}
            className="flex w-full items-center gap-3 border-0 bg-transparent px-3.5 py-2.5 text-left text-sm text-[#2c2620] transition-colors hover:bg-[#faf5ec] cursor-pointer"
          >
            <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-[#eef4fc] text-[#4a7fc1]">
              <FolderOpen className="h-4 w-4" strokeWidth={2} />
            </span>
            <span className="font-medium">{t("chat.input.myDocuments")}</span>
          </button>
        </div>
      )}
    </div>
  );
};
