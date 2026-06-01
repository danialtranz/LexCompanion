import chatService from "@/service/chatService";
import type { ApiEnvelope } from "@/hooks/useDocumentHook";
import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import type { AxiosResponse } from "axios";

export type { ApiEnvelope };

export type AdminDocRetrievalFieldWeights = {
  fields: string[];
};

export type AdminDocRetrievalReferenceFilter = {
  topic_ids?: string[];
  subject_ids?: string[];
  doc_ids?: string[];
};

/** Body gửi lên POST /v1/admin/doc/retrieval */
export type AdminDocRetrievalRequest = {
  query: string;
  session_id?: string | null;
  candidate_size?: number;
  similarity_threshold?: number;
  final_size?: number;
  keyword_weight?: number;
  field_weights?: AdminDocRetrievalFieldWeights;
  reference?: AdminDocRetrievalReferenceFilter;
};

export type RetrievalReferenceItem = {
  index: number;
  ieee: string;
  chunk_id?: string;
  score?: number;
  rerank_score?: number;
  article_id?: string;
  topic_id?: string;
  topic_title?: string;
  subject_id?: string;
  subject_title?: string;
  article_title?: string;
  chapter_title?: string;
  source_link?: string;
  content_text?: string;
  [key: string]: unknown;
};

export type AdminDocRetrievalData = {
  query: string;
  answer: string | null;
  reference: RetrievalReferenceItem[];
};

export type ChatSessionItem = {
  id: string;
  user_id: string;
  title: string | null;
  status: string | null;
  metadata: Record<string, unknown>;
  created_at: string | null;
  updated_at: string | null;
};

export type ChatSessionsListData = {
  total: number;
  page: number;
  page_size: number;
  items: ChatSessionItem[];
};

export type ChatMessageItem = {
  id: string;
  session_id: string;
  user_id: string | null;
  role: string;
  content: string;
  references: RetrievalReferenceItem[];
  created_at: string | null;
};

export type ChatSessionDetailData = {
  session: ChatSessionItem;
  messages: ChatMessageItem[];
};

export type DeleteChatSessionData = {
  session_id: string;
  status: string;
};

export type ChatSessionsQueryParams = {
  page?: number;
  page_size?: number;
};

const CHAT_QK = {
  sessions: (page: number, pageSize: number) =>
    ["chat", "sessions", page, pageSize] as const,
  session: (sessionId: string) => ["chat", "session", sessionId] as const,
};

function isValidSessionId(sessionId: string | null | undefined): boolean {
  if (sessionId === undefined || sessionId === null) return false;
  const s = String(sessionId).trim();
  if (s === "" || s.toLowerCase() === "null") return false;
  return true;
}

const DEFAULT_FIELD_WEIGHTS: AdminDocRetrievalFieldWeights = {
  fields: [
    "article_title^8",
    "subject_title^6",
    "topic_title^5",
    "content_text^2",
  ],
};

function buildRetrievalBody(
  params: AdminDocRetrievalRequest,
): Record<string, unknown> {
  const sessionId = params.session_id?.trim();
  const body: Record<string, unknown> = {
    query: params.query.trim(),
    candidate_size: params.candidate_size ?? 20,
    similarity_threshold: params.similarity_threshold ?? 0.5,
    final_size: params.final_size ?? 5,
    keyword_weight: params.keyword_weight ?? 0.3,
    field_weights: params.field_weights ?? DEFAULT_FIELD_WEIGHTS,
    reference: {
      topic_ids: params.reference?.topic_ids ?? [],
      subject_ids: params.reference?.subject_ids ?? [],
      doc_ids: params.reference?.doc_ids ?? [],
    },
  };
  if (sessionId) {
    body.session_id = sessionId;
  }
  return body;
}

/**
 * Gửi câu hỏi chat / tra cứu pháp điển (ES + rerank + LLM).
 * Backend trả { code, msg, data: { query, answer, reference } }.
 */
export const useChatRetrieval = () => {
  const {
    data,
    isPending: loading,
    isError,
    error,
    mutateAsync,
    reset,
  } = useMutation({
    mutationKey: ["chat", "retrieval"],
    mutationFn: async (
      params: AdminDocRetrievalRequest,
    ): Promise<ApiEnvelope<AdminDocRetrievalData>> => {
      const axiosResponse: AxiosResponse<ApiEnvelope<AdminDocRetrievalData>> =
        await chatService.adminDocRetrieval(buildRetrievalBody(params));
      return axiosResponse.data ?? { code: -1, msg: "Empty response" };
    },
  });

  return {
    data,
    loading,
    isError,
    error,
    retrieve: mutateAsync,
    reset,
  };
};

/**
 * Danh sách phiên chat của user (GET /v1/user/sessions).
 */
export const useChatSessionsList = (params: ChatSessionsQueryParams = {}) => {
  const page = params.page ?? 1;
  const page_size = params.page_size ?? 5;

  return useQuery({
    queryKey: CHAT_QK.sessions(page, page_size),
    placeholderData: keepPreviousData,
    queryFn: async (): Promise<ApiEnvelope<ChatSessionsListData>> => {
      const axiosResponse: AxiosResponse<ApiEnvelope<ChatSessionsListData>> =
        await chatService.listUserChatSessions(
          { params: { page, page_size } },
          true,
        );
      return axiosResponse.data ?? { code: -1, msg: "Empty response" };
    },
  });
};

export async function fetchChatSessionDetail(
  sessionId: string,
): Promise<ApiEnvelope<ChatSessionDetailData>> {
  const axiosResponse: AxiosResponse<ApiEnvelope<ChatSessionDetailData>> =
    await chatService.getUserChatSession(
      { params: { session_id: sessionId } },
      true,
    );
  return axiosResponse.data ?? { code: -1, msg: "Empty response" };
}

/**
 * Chi tiết tin nhắn trong một session (GET /v1/user/session).
 */
export const useChatSessionMessages = (
  sessionId: string | undefined,
  options?: { enabled?: boolean },
) => {
  const enabled = (options?.enabled ?? true) && isValidSessionId(sessionId);

  return useQuery({
    queryKey: CHAT_QK.session(sessionId ?? ""),
    queryFn: () => fetchChatSessionDetail(sessionId!),
    enabled,
  });
};

/**
 * Xóa mềm session chat (DELETE /v1/user/chat).
 */
export const useDeleteChatSession = () => {
  const queryClient = useQueryClient();
  const {
    data,
    isPending: loading,
    mutateAsync,
  } = useMutation({
    mutationKey: ["chat", "deleteSession"],
    mutationFn: async (
      session_id: string,
    ): Promise<ApiEnvelope<DeleteChatSessionData>> => {
      const axiosResponse: AxiosResponse<ApiEnvelope<DeleteChatSessionData>> =
        await chatService.deleteUserChatSession(
          { params: { session_id } },
          true,
        );
      const res = axiosResponse.data ?? { code: -1, msg: "Empty response" };
      if (res.code === 200) {
        queryClient.invalidateQueries({ queryKey: ["chat", "sessions"] });
        queryClient.removeQueries({ queryKey: CHAT_QK.session(session_id) });
      }
      return res;
    },
  });

  return { data, loading, deleteSession: mutateAsync };
};
