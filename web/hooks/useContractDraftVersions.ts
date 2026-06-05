import chatService from "@/service/chatService";
import type { ApiEnvelope } from "@/hooks/useDocumentHook";
import { useQuery } from "@tanstack/react-query";
import type { AxiosResponse } from "axios";

export type ContractDraftVersionItem = {
  version: number;
  draft_object_key?: string;
  draft_output_suffix?: string;
  created_at?: string;
  is_latest?: boolean;
  has_markdown_preview?: boolean;
};

export type ContractDraftVersionsData = {
  session_id: string;
  latest_version: number;
  versions: ContractDraftVersionItem[];
};

export const CONTRACT_DRAFT_VERSIONS_QK = {
  list: (sessionId: string) => ["contract-draft-versions", sessionId] as const,
};

export async function fetchContractDraftVersions(
  sessionId: string,
): Promise<ApiEnvelope<ContractDraftVersionsData>> {
  const axiosResponse: AxiosResponse<
    ApiEnvelope<ContractDraftVersionsData>
  > = await chatService.getContractDraftVersions(
    { params: { session_id: sessionId } },
    true,
  );
  return axiosResponse.data ?? { code: -1, msg: "Empty response" };
}

/**
 * Danh sách phiên bản DOCX nháp (GET /v1/user/contract/draft/versions).
 */
export const useContractDraftVersions = (options: {
  sessionId: string | null;
  enabled?: boolean;
}) => {
  const { sessionId, enabled = true } = options;
  const sid = sessionId?.trim() ?? "";
  const canFetch = enabled && Boolean(sid);

  const query = useQuery({
    queryKey: CONTRACT_DRAFT_VERSIONS_QK.list(sid),
    enabled: canFetch,
    queryFn: () => fetchContractDraftVersions(sid),
    staleTime: 0,
    retry: false,
    refetchOnMount: true,
    refetchOnWindowFocus: false,
  });

  const data =
    query.data?.code === 200 && query.data.data ? query.data.data : null;

  return {
    versions: data?.versions ?? [],
    latestVersion: data?.latest_version,
    loading: query.isLoading || query.isFetching,
    refetch: query.refetch,
    hasVersions: (data?.versions?.length ?? 0) > 0,
  };
};
