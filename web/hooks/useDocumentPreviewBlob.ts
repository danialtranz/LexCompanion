import api from "@/apis/endpoints";
import { getToken } from "@/utils/tokenManager";
import { useQuery } from "@tanstack/react-query";
import {
  fetchContractDraftBinary,
  type ContractDraftBinaryData,
} from "./useContractDraftBinaryPreview";

export type DocumentPreviewBlobData = ContractDraftBinaryData & {
  source: "draft" | "template";
};

export const DOCUMENT_PREVIEW_BLOB_QK = {
  preview: (
    sessionId: string,
    version: number | undefined,
    templateDocId: string | undefined,
  ) =>
    [
      "document-preview-blob",
      sessionId,
      version ?? 0,
      templateDocId ?? "",
    ] as const,
};

export async function fetchDocumentContentBlob(
  docId: string,
): Promise<Blob | null> {
  const token = getToken();
  if (!token || !docId.trim()) return null;

  const params = new URLSearchParams({ doc_id: docId.trim() });
  const res = await fetch(`${api.docContentUrl}?${params}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) return null;

  const blob = await res.blob();
  return blob.size ? blob : null;
}

/**
 * Preview DOCX: ưu tiên bản nháp trên MinIO; chưa có thì lấy văn bản gốc (template).
 */
export async function fetchDocumentPreviewBlob(
  sessionId: string | null,
  version?: number | null,
  templateDocumentId?: string | null,
): Promise<DocumentPreviewBlobData | null> {
  const sid = sessionId?.trim();
  if (sid) {
    const draft = await fetchContractDraftBinary(sid, version);
    if (draft?.blob?.size) {
      return { ...draft, source: "draft" };
    }
  }

  const templateId = templateDocumentId?.trim();
  if (templateId) {
    const blob = await fetchDocumentContentBlob(templateId);
    if (blob?.size) {
      return {
        blob,
        contentType:
          blob.type ||
          "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        source: "template",
      };
    }
  }

  return null;
}

export const useDocumentPreviewBlob = (options: {
  sessionId: string | null;
  viewVersion?: number | null;
  templateDocumentId?: string | null;
  enabled?: boolean;
}) => {
  const {
    sessionId,
    viewVersion,
    templateDocumentId,
    enabled = true,
  } = options;
  const sid = sessionId?.trim() ?? "";
  const tpl = templateDocumentId?.trim() ?? "";
  const canFetch = enabled && (Boolean(tpl) || Boolean(sid));

  const query = useQuery({
    queryKey: DOCUMENT_PREVIEW_BLOB_QK.preview(
      sid,
      viewVersion ?? undefined,
      templateDocumentId?.trim() || undefined,
    ),
    enabled: canFetch,
    queryFn: () =>
      fetchDocumentPreviewBlob(sid, viewVersion, templateDocumentId),
    staleTime: 0,
    retry: false,
  });

  const data = query.data ?? null;

  return {
    blob: data?.blob ?? null,
    source: data?.source,
    draftVersion: data?.draftVersion,
    draftObjectKey: data?.draftObjectKey,
    draftOutputSuffix: data?.draftOutputSuffix,
    contentType: data?.contentType,
    loading: query.isLoading || query.isFetching,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
    hasPreview: Boolean(data?.blob?.size),
  };
};
