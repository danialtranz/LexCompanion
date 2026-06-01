"use client";

import { useCallback, useRef, useState, type DragEvent } from "react";
import { CloudUpload, Loader2 } from "lucide-react";
import toast from "react-hot-toast";
import {
  useUploadUserDocument,
  type UploadUserDocumentData,
} from "@/hooks/useDocumentHook";

const ACCEPT = ".pdf,.docx,.jpg,.jpeg,.png";
const MAX_BYTES = 50 * 1024 * 1024;

type UploadBoxProps = {
  sessionId?: string | null;
  onUploadSuccess?: (data: UploadUserDocumentData) => void;
  disabled?: boolean;
};

function isUploadOk(code: number) {
  return code === 201 || code === 0;
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  const n = bytes / Math.pow(k, i);
  return `${n < 10 && i > 0 ? n.toFixed(1) : Math.round(n)} ${sizes[i]}`;
}

export const UploadBox = ({
  sessionId = null,
  onUploadSuccess,
  disabled = false,
}: UploadBoxProps) => {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const { upload, loading } = useUploadUserDocument();

  const handleFiles = useCallback(
    async (fileList: FileList | null) => {
      if (!fileList?.length || disabled || loading) return;

      const files = Array.from(fileList);
      if (inputRef.current) inputRef.current.value = "";

      for (const file of files) {
        if (file.size > MAX_BYTES) {
          toast.error(`${file.name}: vượt quá 50MB`);
          continue;
        }
        try {
          const res = await upload({ file, session_id: sessionId });
          if (!isUploadOk(res.code) || !res.data) {
            toast.error(res.msg || "Upload thất bại");
            continue;
          }
          onUploadSuccess?.(res.data);
          toast.success(`Đã tải lên: ${res.data.name}`);
        } catch (err) {
          const msg = err instanceof Error ? err.message : "Upload thất bại";
          toast.error(msg);
        }
      }
    },
    [disabled, loading, onUploadSuccess, sessionId, upload],
  );

  const onDragOver = (e: DragEvent) => {
    e.preventDefault();
    if (!disabled && !loading) setIsDragging(true);
  };

  const onDragLeave = () => setIsDragging(false);

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (disabled || loading) return;
    void handleFiles(e.dataTransfer.files);
  };

  return (
    <div
      role="button"
      tabIndex={0}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
      onClick={() => !disabled && !loading && inputRef.current?.click()}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          inputRef.current?.click();
        }
      }}
      className={`rounded-xl border-2 border-dashed px-4 py-8 text-center transition-colors cursor-pointer ${
        isDragging
          ? "border-[#c9a06a] bg-[#faf5ec]"
          : "border-[#e8dcc8] bg-[#faf7f2] hover:border-[#dcc9a8] hover:bg-[#faf5ec]"
      } ${disabled || loading ? "pointer-events-none opacity-60" : ""}`}
    >
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPT}
        multiple
        className="hidden"
        disabled={disabled || loading}
        onChange={(e) => void handleFiles(e.target.files)}
      />

      <div className="mx-auto mb-3 grid h-12 w-12 place-items-center rounded-full bg-[#f5e6cc] text-[#b8874a]">
        {loading ? (
          <Loader2 className="h-6 w-6 animate-spin" strokeWidth={2} />
        ) : (
          <CloudUpload className="h-6 w-6" strokeWidth={2} />
        )}
      </div>

      <p className="m-0 text-[15px] font-bold text-[#5c3d1e]">Upload tài liệu</p>
      <p className="mt-1.5 m-0 text-sm text-[#6b635a]">
        Kéo &amp; thả file vào đây hoặc{" "}
        <span className="font-semibold text-[#9a6c2b] underline-offset-2 hover:underline">
          chọn file
        </span>
      </p>
      <p className="mt-3 m-0 text-xs text-[#8a8178]">
        Hỗ trợ: PDF, DOCX, JPG, PNG (Tối đa {formatBytes(MAX_BYTES)})
      </p>
    </div>
  );
};
