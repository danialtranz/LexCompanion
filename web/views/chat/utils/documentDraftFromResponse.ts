import type { UserConversationData } from "@/hooks/useUserConversation";

export type DocumentDraftPanelState = {
  plainText: string;
  streaming: boolean;
  chunkCurrent?: number;
  chunkTotal?: number;
  statusLabel?: string;
  /** Tăng khi có bản DOCX mới trên MinIO — trigger refetch binary preview. */
  draftVersion?: number;
  /** document_id mẫu gốc — preview lần đầu khi chưa có draft trên MinIO. */
  templateDocumentId?: string;
  /** Bật gọi GET draft/versions + preview/binary từ session. */
  preferMinioHtml?: boolean;
  hasDraftOnStorage?: boolean;
};

function resolveTemplateDocumentId(data: UserConversationData): string {
  const top = (data.template_document_id as string | undefined)?.trim();
  if (top) return top;
  const output = data.output;
  if (output && typeof output === "object") {
    return String((output as Record<string, unknown>).template_document_id || "").trim();
  }
  return "";
}

function resolveDraftObjectKey(data: UserConversationData): string {
  const top = (data.draft_object_key as string | undefined)?.trim();
  if (top) return top;
  const output = data.output;
  if (output && typeof output === "object") {
    return String((output as Record<string, unknown>).draft_object_key || "").trim();
  }
  return "";
}

function resolveDraftVersion(data: UserConversationData): number | undefined {
  const top = data.draft_version;
  if (typeof top === "number") return top;
  const output = data.output;
  if (output && typeof output === "object") {
    const v = (output as Record<string, unknown>).draft_version;
    if (typeof v === "number") return v;
  }
  return undefined;
}

/** Ghép các đoạn preview theo chunk_index (fallback khi chưa có draft đầy đủ). */
export function mergeChunkSections(
  sections: string[],
  chunkIndex: number,
  chunkText: string,
): string[] {
  const next = [...sections];
  const text = (chunkText || "").trim();
  if (!text) return next;
  while (next.length <= chunkIndex) {
    next.push("");
  }
  next[chunkIndex] = text;
  return next;
}

export function sectionsToPlainText(sections: string[]): string {
  return sections
    .filter((s) => (s || "").trim())
    .join("\n\n");
}

function resolveDraftMarkdown(data: UserConversationData): string {
  const top = (data.draft_preview_markdown as string | undefined)?.trim();
  if (top) return top;
  const hitl = data.hitl;
  const fromHitl = (hitl?.draft_preview_markdown as string | undefined)?.trim();
  if (fromHitl) return fromHitl;
  const output = data.output;
  if (output && typeof output === "object") {
    const fromOut = String(
      (output as Record<string, unknown>).draft_preview_markdown || "",
    ).trim();
    if (fromOut) return fromOut;
  }
  return "";
}

export function documentDraftFromResponse(
  data: UserConversationData | undefined,
  prevSections: string[],
): {
  sections: string[];
  panel: DocumentDraftPanelState;
  openDocumentPanel: boolean;
} {
  if (!data || data.ui_template !== "task_execution") {
    return {
      sections: prevSections,
      panel: {
        plainText: sectionsToPlainText(prevSections),
        streaming: false,
      },
      openDocumentPanel: false,
    };
  }

  const draftMarkdown = resolveDraftMarkdown(data);
  const hitl = data.hitl;
  const chunkPreview = (hitl?.chunk_preview as string | undefined)?.trim();
  const chunkIndex =
    typeof hitl?.chunk_index === "number" ? hitl.chunk_index : undefined;
  const chunkTotal =
    typeof hitl?.chunk_total === "number"
      ? hitl.chunk_total
      : typeof data.chunk_total === "number"
        ? data.chunk_total
        : undefined;

  let sections = prevSections;
  if (draftMarkdown) {
    sections = [draftMarkdown];
  } else if (chunkPreview != null && chunkIndex != null) {
    sections = mergeChunkSections(prevSections, chunkIndex, chunkPreview);
  } else if (chunkPreview) {
    sections =
      prevSections.length > 0
        ? mergeChunkSections(prevSections, prevSections.length, chunkPreview)
        : [chunkPreview];
  }

  const plainText = sectionsToPlainText(sections);
  const isWaiting = data.status === "waiting_human";
  const isCompleted = data.status === "completed";
  const statusLabel = isWaiting
    ? "Đang chờ bạn bổ sung thông tin"
    : isCompleted
      ? "Hoàn tất bản nháp"
      : "Agent đang soạn…";
  const draftObjectKey = resolveDraftObjectKey(data);
  const draftVersion = resolveDraftVersion(data);
  const templateDocumentId = resolveTemplateDocumentId(data);

  return {
    sections,
    panel: {
      plainText,
      streaming:
        !isCompleted && (isWaiting || Boolean(draftMarkdown || chunkPreview)),
      chunkCurrent: chunkIndex,
      chunkTotal,
      statusLabel,
      draftVersion,
      templateDocumentId: templateDocumentId || undefined,
      /** Luôn thử MinIO/session APIs trong task_execution (key có thể chỉ ở session metadata). */
      preferMinioHtml: true,
      hasDraftOnStorage: Boolean(draftObjectKey),
    },
    openDocumentPanel: true,
  };
}

export type ContractDraftPreviewData = {
  session_id: string;
  draft_preview_markdown: string;
  filled_values?: Record<string, string>;
  draft_version?: number;
  draft_object_key?: string;
  template_document_id?: string;
};

/** Áp preview từ GET /contract/draft/preview lên panel. */
export function documentDraftFromPreviewApi(
  preview: ContractDraftPreviewData,
  prevSections: string[],
): {
  sections: string[];
  panel: DocumentDraftPanelState;
  openDocumentPanel: boolean;
} {
  const md = (preview.draft_preview_markdown || "").trim();
  if (!md) {
    return {
      sections: prevSections,
      panel: { plainText: sectionsToPlainText(prevSections), streaming: false },
      openDocumentPanel: false,
    };
  }
  return {
    sections: [md],
    panel: {
      plainText: md,
      streaming: false,
      statusLabel: preview.draft_object_key
        ? `Bản nháp v${preview.draft_version ?? ""}`
        : "Bản nháp đã cập nhật",
      draftVersion: preview.draft_version,
      templateDocumentId: preview.template_document_id || undefined,
      preferMinioHtml: Boolean(preview.draft_object_key),
    },
    openDocumentPanel: true,
  };
}
