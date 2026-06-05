import chatService from "@/service/chatService";
import type { ApiEnvelope } from "@/hooks/useDocumentHook";
import { useQuery } from "@tanstack/react-query";
import type { AxiosResponse } from "axios";

export type ContractDraftHtmlPreviewData = {
  session_id: string;
  html: string;
  draft_version?: number;
  draft_object_key?: string;
  draft_output_suffix?: string;
  source?: string;
};

export const CONTRACT_DRAFT_HTML_QK = {
  preview: (sessionId: string, version: number | undefined) =>
    ["contract-draft-html", sessionId, version ?? 0] as const,
};

export async function fetchContractDraftHtmlPreview(
  sessionId: string,
  version?: number | null,
): Promise<ApiEnvelope<ContractDraftHtmlPreviewData>> {
  const params: Record<string, string | number> = { session_id: sessionId };
  if (version != null && version > 0) {
    params.version = version;
  }
  const axiosResponse: AxiosResponse<
    ApiEnvelope<ContractDraftHtmlPreviewData>
  > = await chatService.getContractDraftPreviewHtml({ params }, true);
  return axiosResponse.data ?? { code: -1, msg: "Empty response" };
}

/**
 * Preview HTML từ DOCX nháp trên MinIO (GET /v1/user/contract/draft/preview/html).
 */
export const useContractDraftHtmlPreview = (options: {
  sessionId: string | null;
  /** Phiên bản đang xem; null/undefined = mới nhất. */
  viewVersion?: number | null;
  enabled?: boolean;
}) => {
  const { sessionId, viewVersion, enabled = true } = options;
  const canFetch = enabled && Boolean(sessionId?.trim());
  const versionKey = viewVersion ?? 0;

  const query = useQuery({
    queryKey: CONTRACT_DRAFT_HTML_QK.preview(sessionId ?? "", versionKey),
    enabled: canFetch,
    queryFn: () =>
      fetchContractDraftHtmlPreview(sessionId!.trim(), viewVersion),
    staleTime: 0,
    retry: false,
  });

  const html =
    query.data?.code === 200 && query.data.data?.html
      ? query.data.data.html
      : null;

  return {
    html,
    draftVersion: query.data?.data?.draft_version,
    loading: query.isLoading || query.isFetching,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
    hasMinioPreview: Boolean(html),
  };
};
