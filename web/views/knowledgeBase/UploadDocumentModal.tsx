"use client";

import { useCallback, useRef, useState } from "react";
import { Upload, X } from "lucide-react";
import toast from "react-hot-toast";
import {
  useUploadDocument,
  type UploadDocumentData,
} from "@/hooks/useDocumentHook";

type UploadDocumentModalProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onUploadSuccess?: (data: UploadDocumentData) => void;
  kb_id?: string | null;
};

const ACCEPT =
  ".pdf,.doc,.docx,.txt,.md,.csv,.xlsx,.ppt,.pptx,application/pdf,application/msword";

function isUploadOk(code: number) {
  return code === 201 || code === 0;
}

export function UploadDocumentModal({
  open,
  onOpenChange,
  onUploadSuccess,
  kb_id = null,
}: UploadDocumentModalProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const { upload, loading: uploading } = useUploadDocument();

  const handleFiles = useCallback(
    async (fileList: FileList | null) => {
      if (!fileList?.length) return;
      const files = Array.from(fileList);
      if (inputRef.current) inputRef.current.value = "";

      const run = async () => {
        for (const file of files) {
          const res = await upload({ file, kb_id });
          if (!isUploadOk(res.code) || !res.data) {
            throw new Error(res.msg || "Upload failed");
          }
          onUploadSuccess?.(res.data);
        }
      };

      try {
        await toast.promise(run(), {
          loading:
            files.length > 1
              ? `Uploading ${files.length} files…`
              : "Uploading…",
          success:
            files.length > 1
              ? `${files.length} files uploaded`
              : "File uploaded",
          error: (err: Error) => err.message || "Upload failed",
        });
        onOpenChange(false);
      } catch {
        /* toast.promise already showed error */
      }
    },
    [upload, kb_id, onUploadSuccess, onOpenChange],
  );

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6"
      role="dialog"
      aria-modal="true"
      aria-labelledby="upload-doc-title"
    >
      <button
        type="button"
        className="absolute inset-0 z-0 bg-stone-900/25 backdrop-blur-sm transition-opacity"
        aria-label="Close"
        onClick={() => !uploading && onOpenChange(false)}
      />
      <div className="relative z-10 w-full max-w-lg">
        <div className="overflow-hidden rounded-2xl border border-stone-200/80 bg-[#fefdfb] shadow-2xl shadow-stone-300/40 ring-1 ring-white/80">
          <div className="flex items-start justify-between gap-3 border-b border-stone-100 px-5 py-4 sm:px-6">
            <div>
              <h2
                id="upload-doc-title"
                className="text-lg font-semibold tracking-tight text-stone-900"
              >
                Upload documents
              </h2>
              <p className="mt-1 text-sm text-stone-500">
                Drag files here or choose from your device. Supported: PDF, Word,
                text, and spreadsheets.
              </p>
            </div>
            <button
              type="button"
              disabled={uploading}
              onClick={() => onOpenChange(false)}
              className="shrink-0 rounded-lg p-2 text-stone-400 transition hover:bg-stone-100 hover:text-stone-700 disabled:opacity-40"
              aria-label="Close dialog"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          <div className="p-5 sm:p-6">
            <div
              onDragEnter={(e) => {
                e.preventDefault();
                if (!uploading) setIsDragging(true);
              }}
              onDragLeave={(e) => {
                e.preventDefault();
                if (!e.currentTarget.contains(e.relatedTarget as Node)) {
                  setIsDragging(false);
                }
              }}
              onDragOver={(e) => {
                e.preventDefault();
                e.dataTransfer.dropEffect = uploading ? "none" : "copy";
              }}
              onDrop={(e) => {
                e.preventDefault();
                setIsDragging(false);
                if (uploading) return;
                handleFiles(e.dataTransfer.files);
              }}
              className={[
                "flex min-h-[200px] flex-col items-center justify-center rounded-xl border-2 border-dashed px-4 py-10 text-center transition-all",
                uploading
                  ? "cursor-wait border-stone-200 bg-stone-50/90 opacity-80"
                  : isDragging
                    ? "border-violet-400 bg-violet-50/80 shadow-inner shadow-violet-100"
                    : "border-stone-200 bg-gradient-to-b from-white to-stone-50/80 hover:border-stone-300",
              ].join(" ")}
            >
              <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-100 to-fuchsia-100 text-violet-600 shadow-sm ring-1 ring-violet-200/60">
                <Upload className="h-7 w-7" strokeWidth={1.75} />
              </div>
              <p className="text-sm font-medium text-stone-800">
                {uploading ? "Uploading…" : "Drop files to upload"}
              </p>
              <p className="mt-1 text-xs text-stone-500">or</p>
              <button
                type="button"
                disabled={uploading}
                onClick={() => inputRef.current?.click()}
                className="mt-4 rounded-xl bg-gradient-to-r from-violet-600 to-fuchsia-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-violet-500/25 transition hover:from-violet-500 hover:to-fuchsia-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-violet-400 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
              >
                Browse files
              </button>
              <input
                ref={inputRef}
                type="file"
                className="hidden"
                multiple
                accept={ACCEPT}
                disabled={uploading}
                onChange={(e) => void handleFiles(e.target.files)}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
