import api from "@/apis/endpoints";
import { getToken } from "@/utils/tokenManager";
import { useQuery } from "@tanstack/react-query";

export type ContractDraftBinaryData = {
  blob: Blob;
  contentType: string;
  draftVersion?: number;
  draftObjectKey?: string;
  draftOutputSuffix?: string;
};

export const CONTRACT_DRAFT_BINARY_QK = {
  preview: (sessionId: string, version: number | undefined) =>
    ["contract-draft-binary", sessionId, version ?? 0] as const,
};

function parseDraftVersionHeader(value: string | null): number | undefined {
  if (!value) return undefined;
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) ? parsed : undefined;
}

/**
 * Tải DOCX nháp từ MinIO dạng binary (GET /v1/user/contract/draft/preview/binary).
 */
export async function fetchContractDraftBinary(
  sessionId: string,
  version?: number | null,
): Promise<ContractDraftBinaryData | null> {
  const token = getToken();
  if (!token) return null;

  const search = new URLSearchParams({ session_id: sessionId });
  if (version != null && version > 0) {
    search.set("version", String(version));
  }

  const res = await fetch(
    `${api.userContractDraftPreviewBinaryUrl}?${search}`,
    { headers: { Authorization: `Bearer ${token}` } },
  );
  if (!res.ok) return null;

  const blob = await res.blob();
  if (!blob.size) return null;

  return {
    blob,
    contentType:
      res.headers.get("Content-Type") ??
      blob.type ??
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    draftVersion: parseDraftVersionHeader(res.headers.get("X-Draft-Version")),
    draftObjectKey: res.headers.get("X-Draft-Object-Key") ?? undefined,
    draftOutputSuffix: res.headers.get("X-Draft-Output-Suffix") ?? undefined,
  };
}

/**
 * Hook tải DOCX nháp binary — render read-only bằng docx-preview.
 */
export const useContractDraftBinaryPreview = (options: {
  sessionId: string | null;
  viewVersion?: number | null;
  enabled?: boolean;
}) => {
  const { sessionId, viewVersion, enabled = true } = options;
  const canFetch = enabled && Boolean(sessionId?.trim());
  const versionKey = viewVersion ?? 0;

  const query = useQuery({
    queryKey: CONTRACT_DRAFT_BINARY_QK.preview(sessionId ?? "", versionKey),
    enabled: canFetch,
    queryFn: () =>
      fetchContractDraftBinary(sessionId!.trim(), viewVersion),
    staleTime: 0,
    retry: false,
  });

  const data = query.data ?? null;

  return {
    blob: data?.blob ?? null,
    draftVersion: data?.draftVersion,
    draftObjectKey: data?.draftObjectKey,
    draftOutputSuffix: data?.draftOutputSuffix,
    contentType: data?.contentType,
    loading: query.isLoading || query.isFetching,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
    hasMinioPreview: Boolean(data?.blob?.size),
  };
};
