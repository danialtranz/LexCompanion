"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { Eye, Loader2, Search, Trash2, X } from "lucide-react";
import toast from "react-hot-toast";
import { api_host } from "@/apis/endpoints";
import { getToken } from "@/utils/tokenManager";
import {
  useDeleteDocument,
  useDocumentsList,
  type DocumentListItem,
} from "@/hooks/useDocumentHook";

type FileTableProps = {
  kb_id?: string | null;
  page_size?: number;
};

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  const n = bytes / Math.pow(k, i);
  return `${n < 10 && i > 0 ? n.toFixed(1) : Math.round(n)} ${sizes[i]}`;
}

function formatCreateDate(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function RunControl({ run, onRun }: { run: string; onRun: () => void }) {
  if (run === "1") {
    return (
      <span className="text-sm font-medium text-emerald-700">Thành công</span>
    );
  }
  if (run === "0") {
    return (
      <button
        type="button"
        onClick={onRun}
        className="shrink-0 rounded-lg border border-violet-300 bg-violet-50 px-3 py-1.5 text-xs font-semibold text-violet-800 transition hover:bg-violet-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-violet-400"
      >
        Chạy
      </button>
    );
  }
  return <span className="text-sm font-medium text-rose-600">failed</span>;
}

function canEmbedInIframe(fileType: string): boolean {
  const t = fileType.toLowerCase();
  if (t === "pdf") return true;
  return ["png", "jpg", "jpeg", "gif", "webp", "svg"].includes(t);
}

/** Lấy file qua API (JWT) rồi tạo blob: URL — iframe không cần presigned MinIO. */
function usePreviewBlobUrl(docId: string | undefined, enabled: boolean) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [blobError, setBlobError] = useState(false);

  useEffect(() => {
    if (!enabled || !docId) {
      setBlobUrl(null);
      setBlobError(false);
      return;
    }

    setBlobError(false);
    let revoked = false;
    let objectUrl: string | null = null;

    (async () => {
      try {
        const token = getToken();
        if (!token) throw new Error("no token");
        const params = new URLSearchParams({ doc_id: docId });
        const res = await fetch(`${api_host}/v1/doc/content?${params}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error("fetch failed");
        const blob = await res.blob();
        if (revoked) return;
        objectUrl = URL.createObjectURL(blob);
        setBlobUrl(objectUrl);
      } catch {
        if (!revoked) {
          setBlobUrl(null);
          setBlobError(true);
        }
      }
    })();

    return () => {
      revoked = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
      setBlobUrl(null);
    };
  }, [docId, enabled]);

  const displayUrl = blobUrl;
  const blobLoading = enabled && !!docId && !blobUrl && !blobError;
  const fetchFailed = enabled && !!docId && blobError;

  return { displayUrl, blobLoading, fetchFailed };
}

async function openDocumentBlobInNewTab(docId: string): Promise<void> {
  const token = getToken();
  if (!token) {
    toast.error("Chưa đăng nhập");
    return;
  }
  const params = new URLSearchParams({ doc_id: docId });
  const res = await fetch(`${api_host}/v1/doc/content?${params}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    toast.error("Không tải được tài liệu");
    return;
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  window.open(url, "_blank", "noopener,noreferrer");
  window.setTimeout(() => URL.revokeObjectURL(url), 120_000);
}

export function FileTable({ kb_id = null, page_size = 5 }: FileTableProps) {
  const [page, setPage] = useState(1);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [preview, setPreview] = useState<{
    id: string;
    name: string;
    type: string;
  } | null>(null);

  const {
    data: envelope,
    isPending,
    isError,
    error,
    refetch,
  } = useDocumentsList({ kb_id, page, page_size });

  const listPayload = envelope?.code === 0 ? envelope.data : undefined;
  const items = listPayload?.items ?? [];
  const total = listPayload?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / page_size));

  const { deleteDocument } = useDeleteDocument();

  const fetchPreviewBlob = !!preview?.id && canEmbedInIframe(preview.type);

  const { displayUrl, blobLoading, fetchFailed } = usePreviewBlobUrl(
    preview?.id,
    fetchPreviewBlob,
  );

  const handleRun = useCallback((item: DocumentListItem) => {
    toast.success(`Đã chọn chạy xử lý: ${item.name}`);
  }, []);

  const handleDelete = useCallback(
    async (docId: string, name: string) => {
      if (!window.confirm(`Xóa tài liệu "${name}"?`)) return;
      setDeletingId(docId);
      try {
        const code = await deleteDocument(docId);
        if (code === 0) {
          toast.success("Đã xóa tài liệu");
          if (items.length === 1 && page > 1) {
            setPage((p) => Math.max(1, p - 1));
          }
        } else {
          toast.error("Không xóa được tài liệu");
        }
      } catch {
        toast.error("Không xóa được tài liệu");
      } finally {
        setDeletingId(null);
      }
    },
    [deleteDocument, items.length, page],
  );

  const rangeLabel = useMemo(() => {
    if (total === 0) return "0 / 0";
    const start = (page - 1) * page_size + 1;
    const end = Math.min(page * page_size, total);
    return `${start}–${end} / ${total}`;
  }, [total, page, page_size]);

  const empty = !isPending && items.length === 0 && envelope?.code === 0;
  const loadError = isError || (envelope && envelope.code !== 0);

  const closePreview = useCallback(() => setPreview(null), []);

  return (
    <section className="w-full">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-xl font-bold tracking-tight text-stone-900 sm:text-2xl">
          Uploaded
        </h2>
        <button
          type="button"
          onClick={() => void refetch()}
          className="self-start text-sm font-medium text-violet-700 hover:underline sm:self-auto"
        >
          Làm mới
        </button>
      </div>

      <div className="mt-4 overflow-hidden rounded-2xl border border-stone-200/90 bg-white/80 shadow-sm ring-1 ring-stone-100/80">
        {isPending && items.length === 0 ? (
          <div className="flex min-h-[200px] items-center justify-center gap-2 py-16 text-stone-500">
            <Loader2 className="h-6 w-6 animate-spin" />
            <span>Đang tải…</span>
          </div>
        ) : loadError ? (
          <div className="px-4 py-12 text-center text-sm text-rose-600">
            {envelope && envelope.code !== 0
              ? envelope.msg || "Không tải được danh sách"
              : (error as Error)?.message || "Không tải được danh sách"}
          </div>
        ) : empty ? (
          <div className="flex min-h-[240px] flex-col items-center justify-center px-4 py-16 text-center sm:min-h-[280px]">
            <div className="mb-4 flex h-20 w-20 items-center justify-center rounded-full bg-stone-100 text-stone-400 ring-1 ring-stone-200/80">
              <Search className="h-10 w-10 stroke-[1.25]" />
            </div>
            <p className="text-sm font-medium text-stone-500">
              Chưa có dữ liệu
            </p>
            <p className="mt-1 max-w-xs text-xs text-stone-400">
              Tải tài liệu lên để hiển thị tại đây.
            </p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[880px] text-left text-sm">
                <thead>
                  <tr className="border-b border-stone-200 bg-stone-50/90 text-xs font-semibold uppercase tracking-wide text-stone-500">
                    <th className="px-3 py-3 sm:px-4">Name</th>
                    <th className="px-3 py-3 sm:px-4">Type</th>
                    <th className="px-3 py-3 sm:px-4">Size</th>
                    <th className="px-3 py-3 sm:px-4">Create date</th>
                    <th className="px-3 py-3 text-right sm:px-4">
                      Xem / Run / Xóa
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-stone-100">
                  {items.map((row) => (
                    <tr
                      key={row.id}
                      className="transition hover:bg-stone-50/80"
                    >
                      <td className="max-w-[220px] truncate px-3 py-3 font-medium text-stone-800 sm:px-4">
                        {row.name}
                      </td>
                      <td className="px-3 py-3 text-stone-600 sm:px-4">
                        {row.type}
                      </td>
                      <td className="whitespace-nowrap px-3 py-3 text-stone-600 sm:px-4">
                        {formatBytes(row.size)}
                      </td>
                      <td className="whitespace-nowrap px-3 py-3 text-stone-600 sm:px-4">
                        {formatCreateDate(row.create_date)}
                      </td>
                      <td className="px-3 py-3 sm:px-4">
                        <div className="flex flex-wrap items-center justify-end gap-2">
                          <RunControl
                            run={row.run}
                            onRun={() => handleRun(row)}
                          />
                          <button
                            type="button"
                            onClick={() =>
                              setPreview({
                                id: row.id,
                                name: row.name,
                                type: row.type,
                              })
                            }
                            className="inline-flex shrink-0 items-center justify-center rounded-lg border border-stone-200 bg-white p-2 text-stone-500 transition hover:border-sky-200 hover:bg-sky-50 hover:text-sky-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
                            title="Xem trước"
                            aria-label={`Xem ${row.name}`}
                          >
                            <Eye className="h-4 w-4" strokeWidth={1.75} />
                          </button>
                          <button
                            type="button"
                            disabled={deletingId === row.id}
                            onClick={() => void handleDelete(row.id, row.name)}
                            className="inline-flex shrink-0 items-center justify-center rounded-lg border border-stone-200 bg-white p-2 text-stone-500 transition hover:border-rose-200 hover:bg-rose-50 hover:text-rose-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-rose-400 disabled:opacity-50"
                            title="Xóa"
                            aria-label={`Xóa ${row.name}`}
                          >
                            {deletingId === row.id ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <Trash2 className="h-4 w-4" strokeWidth={1.75} />
                            )}
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {total > 0 && (
              <div className="flex flex-col gap-3 border-t border-stone-100 bg-stone-50/50 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-xs text-stone-600 sm:text-sm">
                  Hiển thị <span className="font-medium">{rangeLabel}</span>
                </p>
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    disabled={page <= 1 || isPending}
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    className="rounded-lg border border-stone-200 bg-white px-3 py-1.5 text-xs font-medium text-stone-700 transition hover:bg-stone-50 disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    Trước
                  </button>
                  <span className="text-xs text-stone-600">
                    Trang {page} / {totalPages}
                  </span>
                  <button
                    type="button"
                    disabled={page >= totalPages || isPending}
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    className="rounded-lg border border-stone-200 bg-white px-3 py-1.5 text-xs font-medium text-stone-700 transition hover:bg-stone-50 disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    Sau
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {preview &&
        typeof document !== "undefined" &&
        createPortal(
          <div
            className="fixed inset-0 z-[200] flex items-center justify-center p-4 sm:p-6"
            role="dialog"
            aria-modal="true"
            aria-labelledby="doc-preview-title"
          >
            <button
              type="button"
              className="absolute inset-0 z-0 bg-stone-900/40 backdrop-blur-sm"
              aria-label="Đóng"
              onClick={closePreview}
            />
            <div
              className="relative z-10 flex max-h-[90vh] w-full max-w-5xl flex-col overflow-hidden rounded-2xl border border-stone-200/80 bg-[#fefdfb] shadow-2xl ring-1 ring-white/80"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between gap-3 border-b border-stone-100 px-4 py-3 sm:px-5">
                <h3
                  id="doc-preview-title"
                  className="min-w-0 truncate text-base font-semibold text-stone-900"
                >
                  Xem: {preview.name}
                </h3>
                <button
                  type="button"
                  onClick={closePreview}
                  className="shrink-0 rounded-lg p-2 text-stone-400 transition hover:bg-stone-100 hover:text-stone-800"
                  aria-label="Đóng"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              <div className="min-h-[70vh] max-h-[min(85vh,800px)] flex-1 bg-stone-100/80">
                {canEmbedInIframe(preview.type) &&
                  (blobLoading ? (
                    <div className="flex h-[70vh] max-h-[min(85vh,800px)] items-center justify-center gap-2 text-stone-500">
                      <Loader2 className="h-8 w-8 animate-spin" />
                      <span>Đang tải nội dung…</span>
                    </div>
                  ) : displayUrl ? (
                    <iframe
                      title={preview.name}
                      src={displayUrl}
                      className="h-[70vh] max-h-[min(85vh,800px)] w-full border-0 bg-white"
                    />
                  ) : fetchFailed ? (
                    <div className="flex h-[70vh] max-h-[min(85vh,800px)] flex-col items-center justify-center gap-3 px-6 text-center">
                      <p className="text-sm text-stone-600">
                        Không tải được tài liệu. Kiểm tra đăng nhập hoặc thử lại
                        sau.
                      </p>
                      <button
                        type="button"
                        onClick={() => void openDocumentBlobInNewTab(preview.id)}
                        className="rounded-xl bg-gradient-to-r from-violet-600 to-fuchsia-600 px-5 py-2.5 text-sm font-semibold text-white shadow-md transition hover:from-violet-500 hover:to-fuchsia-500"
                      >
                        Thử mở trong tab mới
                      </button>
                    </div>
                  ) : null)}

                {!canEmbedInIframe(preview.type) && (
                  <div className="flex h-[70vh] max-h-[min(85vh,800px)] flex-col items-center justify-center gap-4 px-6 text-center">
                    <p className="text-sm text-stone-600">
                      Định dạng này không nhúng trực tiếp. Mở trong tab mới để
                      xem (hoặc dùng ứng dụng mặc định).
                    </p>
                    <button
                      type="button"
                      onClick={() =>
                        void openDocumentBlobInNewTab(preview.id).catch(() =>
                          toast.error("Không mở được tài liệu"),
                        )
                      }
                      className="rounded-xl bg-gradient-to-r from-violet-600 to-fuchsia-600 px-5 py-2.5 text-sm font-semibold text-white shadow-md transition hover:from-violet-500 hover:to-fuchsia-500"
                    >
                      Xem trong tab mới
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>,
          document.body,
        )}
    </section>
  );
}
