import chatService from "@/service/chatService";
import type { ApiEnvelope } from "@/hooks/useDocumentHook";
import { useMutation } from "@tanstack/react-query";
import type { AxiosResponse } from "axios";

export type { ApiEnvelope };

export type AdminDocRetrievalFieldWeights = {
  fields: string[];
};

export type AdminDocRetrievalReferenceFilter = {
  topic_ids?: string[];
  subject_ids?: string[];
};

/** Body gửi lên POST /v1/admin/doc/retrieval */
export type AdminDocRetrievalRequest = {
  query: string;
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
  return {
    query: params.query.trim(),
    candidate_size: params.candidate_size ?? 20,
    similarity_threshold: params.similarity_threshold ?? 0.5,
    final_size: params.final_size ?? 5,
    keyword_weight: params.keyword_weight ?? 0.3,
    field_weights: params.field_weights ?? DEFAULT_FIELD_WEIGHTS,
    reference: {
      topic_ids: params.reference?.topic_ids ?? [],
      subject_ids: params.reference?.subject_ids ?? [],
    },
  };
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
