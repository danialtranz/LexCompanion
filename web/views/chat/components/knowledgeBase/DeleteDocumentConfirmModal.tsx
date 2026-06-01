"use client";

import { Loader2 } from "lucide-react";

type DeleteDocumentConfirmModalProps = {
  open: boolean;
  fileName: string;
  loading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
};

export const DeleteDocumentConfirmModal = ({
  open,
  fileName,
  loading = false,
  onConfirm,
  onCancel,
}: DeleteDocumentConfirmModalProps) => {
  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="delete-doc-title"
    >
      <button
        type="button"
        className="absolute inset-0 bg-[#2c2620]/30 backdrop-blur-[2px]"
        aria-label="Đóng"
        disabled={loading}
        onClick={onCancel}
      />
      <div className="relative z-10 w-full max-w-sm overflow-hidden rounded-2xl border border-[#ebe3d6] bg-[#fefdfb] shadow-xl shadow-[#c9a06a]/15">
        <div className="border-b border-[#f3ece2] px-5 py-4">
          <h2
            id="delete-doc-title"
            className="m-0 text-base font-bold text-[#2c2620]"
          >
            Xóa tài liệu?
          </h2>
          <p className="mt-2 m-0 text-sm text-[#6b635a]">
            Bạn có chắc muốn xóa{" "}
            <span className="font-medium text-[#2c2620]">&quot;{fileName}&quot;</span>
            ? Hành động này không thể hoàn tác.
          </p>
        </div>
        <div className="flex justify-end gap-2 px-5 py-4">
          <button
            type="button"
            disabled={loading}
            onClick={onCancel}
            className="rounded-xl border border-[#ebe3d6] bg-[#faf7f2] px-4 py-2 text-sm font-medium text-[#6b635a] transition-colors hover:border-[#dcc9a8] hover:bg-[#f5efe4] disabled:opacity-60 cursor-pointer"
          >
            Không
          </button>
          <button
            type="button"
            disabled={loading}
            onClick={onConfirm}
            className="inline-flex min-w-[72px] items-center justify-center gap-1.5 rounded-xl border-0 bg-[#c45c4a] px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-[#b04f3f] disabled:opacity-60 cursor-pointer"
          >
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" strokeWidth={2} />
                Đang xóa…
              </>
            ) : (
              "Có"
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
