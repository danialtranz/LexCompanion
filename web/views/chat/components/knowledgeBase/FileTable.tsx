"use client";

import { useCallback, useState } from "react";
import {
  ChevronRight,
  FileText,
  Image as ImageIcon,
  Loader2,
  Trash2,
} from "lucide-react";
import toast from "react-hot-toast";
import { useTranslation } from "react-i18next";
import {
  useDeleteDocument,
  useDocumentsList,
  type DocumentListItem,
} from "@/hooks/useDocumentHook";
import { DeleteDocumentConfirmModal } from "./DeleteDocumentConfirmModal";
import { useKbDocumentRowDrag } from "@/views/chat/utils/useKbDocumentRowDrag";

type FileKind = "pdf" | "word" | "image" | "other";

type FileTableProps = {
  kb_id?: string | null;
  page?: number;
  page_size?: number;
  onViewAll?: () => void;
  maxVisible?: number;
};

function resolveFileKind(item: DocumentListItem): FileKind {
  const raw = `${item.type} ${item.suffix} ${item.name}`.toLowerCase();
  if (raw.includes("pdf")) return "pdf";
  if (/\b(docx?|word)\b/.test(raw) || raw.includes(".doc")) return "word";
  if (/\b(png|jpe?g|gif|webp)\b/.test(raw)) return "image";
  return "other";
}

function isProcessingComplete(progress: number): boolean {
  return progress >= 1;
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  const n = bytes / Math.pow(k, i);
  return `${n < 10 && i > 0 ? n.toFixed(1) : Math.round(n)} ${sizes[i]}`;
}

function DocumentTypeIcon({ kind }: { kind: FileKind }) {
  switch (kind) {
    case "pdf":
      return (
        <div className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-[#fdf0ed] text-[#c45c4a]">
          <FileText className="h-[18px] w-[18px]" strokeWidth={2} />
        </div>
      );
    case "word":
      return (
        <div className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-[#eef4fc] text-[#4a7fc1]">
          <FileText className="h-[18px] w-[18px]" strokeWidth={2} />
        </div>
      );
    case "image":
      return (
        <div className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-[#f0f5ec] text-[#6b8f4e]">
          <ImageIcon className="h-[18px] w-[18px]" strokeWidth={2} />
        </div>
      );
    default:
      return (
        <div className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-[#f5efe4] text-[#8a8178]">
          <FileText className="h-[18px] w-[18px]" strokeWidth={2} />
        </div>
      );
  }
}

type FileTableRowProps = {
  file: DocumentListItem;
  deletingId: string | null;
  deleteLoading: boolean;
  onRequestDelete: () => void;
};

function FileTableRow({
  file,
  deletingId,
  deleteLoading,
  onRequestDelete,
}: FileTableRowProps) {
  const { t } = useTranslation();
  const ready = isProcessingComplete(file.progress);
  const { draggable, onDragStart, title } = useKbDocumentRowDrag(file);

  return (
    <li
      draggable={draggable}
      onDragStart={onDragStart}
      title={title}
      className={`flex items-center gap-3 rounded-xl border px-3 py-2.5 transition-colors ${
        ready
          ? "border-[#dcc9a8] bg-[#faf7f2] shadow-[0_1px_0_rgba(201,160,106,0.12)] cursor-grab active:cursor-grabbing"
          : "border-[#ebe3d6] bg-[#faf7f2]/50 opacity-60 saturate-50"
      }`}
    >
      <DocumentTypeIcon kind={resolveFileKind(file)} />
      <div className="min-w-0 flex-1">
        <p
          className={`m-0 truncate text-sm font-medium ${
            ready ? "text-[#2c2620]" : "text-[#8a8178]"
          }`}
        >
          {file.name}
        </p>
        <p className="mt-0.5 m-0 text-xs text-[#8a8178]">
          {formatBytes(file.size)}
          {!ready && (
            <span className="text-[#b5a99a]">
              {" "}
              · {t("chat.knowledgeBase.processing")}
            </span>
          )}
        </p>
      </div>
      <button
        type="button"
        disabled={!ready || deletingId === file.id || deleteLoading}
        aria-label={t("common.deleteNamed", { name: file.name })}
        onClick={onRequestDelete}
        className="grid h-8 w-8 shrink-0 place-items-center rounded-lg border-0 bg-transparent text-[#8a8178] transition-colors enabled:cursor-pointer enabled:hover:bg-[#faf5ec] enabled:hover:text-[#c45c4a] disabled:cursor-not-allowed disabled:opacity-40"
      >
        {deletingId === file.id ? (
          <Loader2 className="h-4 w-4 animate-spin" strokeWidth={2} />
        ) : (
          <Trash2 className="h-4 w-4" strokeWidth={2} />
        )}
      </button>
    </li>
  );
}

export const FileTable = ({
  kb_id = null,
  page: pageProp = 1,
  page_size = 7,
  onViewAll,
  maxVisible = 7,
}: FileTableProps) => {
  const { t } = useTranslation();
  const [pendingDelete, setPendingDelete] = useState<{
    id: string;
    name: string;
  } | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const { deleteDocument, loading: deleteLoading } = useDeleteDocument();

  const {
    data: envelope,
    isPending,
    isError,
    error,
  } = useDocumentsList({
    kb_id,
    page: pageProp,
    page_size,
  });

  const listPayload = envelope?.code === 0 ? envelope.data : undefined;
  const items = listPayload?.items ?? [];
  const total = listPayload?.total ?? 0;
  const visible = items.slice(0, maxVisible);
  const hasMore = total > maxVisible;

  const loadError = isError || (envelope != null && envelope.code !== 0);

  const confirmDelete = useCallback(async () => {
    if (!pendingDelete) return;
    const { id: docId } = pendingDelete;
    setDeletingId(docId);
    try {
      const code = await deleteDocument(docId);
      if (code === 0) {
        toast.success(t("chat.knowledgeBase.deleteSuccess"));
        setPendingDelete(null);
      } else {
        toast.error(t("chat.knowledgeBase.deleteFailed"));
      }
    } catch {
      toast.error(t("chat.knowledgeBase.deleteFailed"));
    } finally {
      setDeletingId(null);
    }
  }, [deleteDocument, pendingDelete, t]);

  return (
    <section className="mt-6 min-h-0 flex-1 flex flex-col">
      <div>
        <h3 className="m-0 text-sm font-bold text-[#2c2620]">
          {t("chat.knowledgeBase.documentsTitle")}
        </h3>
        <p className="mt-1 m-0 text-xs text-[#8a8178]">
          {t("chat.knowledgeBase.dragHint")}
        </p>
      </div>

      <ul className="mt-3 flex-1 space-y-2 overflow-y-auto">
        {isPending && items.length === 0 ? (
          <li className="flex items-center justify-center gap-2 rounded-lg border border-dashed border-[#ebe3d6] bg-[#faf7f2] px-4 py-8 text-sm text-[#8a8178]">
            <Loader2 className="h-4 w-4 animate-spin" strokeWidth={2} />
            {t("chat.knowledgeBase.loadingList")}
          </li>
        ) : loadError ? (
          <li className="rounded-lg border border-dashed border-[#f0d4d0] bg-[#fdf8f7] px-4 py-8 text-center text-sm text-[#c45c4a]">
            {envelope && envelope.code !== 0
              ? envelope.msg || t("chat.knowledgeBase.loadListFailed")
              : (error as Error)?.message || t("chat.knowledgeBase.loadListFailed")}
          </li>
        ) : visible.length === 0 ? (
          <li className="rounded-lg border border-dashed border-[#ebe3d6] bg-[#faf7f2] px-4 py-8 text-center text-sm text-[#8a8178]">
            {t("chat.knowledgeBase.emptyList")}
          </li>
        ) : (
          visible.map((file) => (
            <FileTableRow
              key={file.id}
              file={file}
              deletingId={deletingId}
              deleteLoading={deleteLoading}
              onRequestDelete={() =>
                setPendingDelete({ id: file.id, name: file.name })
              }
            />
          ))
        )}
      </ul>

      {hasMore && onViewAll && (
        <button
          type="button"
          onClick={onViewAll}
          className="mt-4 flex w-full items-center justify-center gap-1 rounded-xl border border-[#ebe3d6] bg-[#faf7f2] py-2.5 text-sm font-medium text-[#6b635a] transition-colors hover:border-[#dcc9a8] hover:bg-[#f5efe4] cursor-pointer"
        >
          {t("chat.knowledgeBase.viewAllDocuments", { count: total })}
          <ChevronRight className="h-4 w-4" strokeWidth={2} />
        </button>
      )}

      <DeleteDocumentConfirmModal
        open={pendingDelete != null}
        fileName={pendingDelete?.name ?? ""}
        loading={deleteLoading && deletingId === pendingDelete?.id}
        onConfirm={() => void confirmDelete()}
        onCancel={() => {
          if (!deleteLoading) setPendingDelete(null);
        }}
      />
    </section>
  );
};
