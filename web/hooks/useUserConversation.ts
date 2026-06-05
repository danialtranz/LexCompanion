import chatService from "@/service/chatService";
import type { ApiEnvelope } from "@/hooks/useDocumentHook";
import type {
  AdminDocRetrievalFieldWeights,
  AdminDocRetrievalReferenceFilter,
  RetrievalReferenceItem,
} from "@/hooks/useChatHook";
import { useMutation } from "@tanstack/react-query";
import type { AxiosResponse } from "axios";

export type UserConversationHitl = {
  kind?: string;
  interrupt_id?: string;
  chunk_index?: number;
  chunk_total?: number;
  chunk_preview?: string;
  draft_preview_markdown?: string;
  form_schema?: unknown[];
  missing_field_ids?: string[];
  filled_values?: Record<string, string>;
  clarification_questions?: string[];
  actions?: string[];
  [key: string]: unknown;
};

export type UserConversationResume = {
  action?: string;
  payload?: Record<string, unknown>;
  [key: string]: unknown;
};

/** Body gửi lên POST /v1/user/user_chat */
export type UserConversationRequest = {
  query: string;
  session_id?: string | null;
  stream?: boolean;
  candidate_size?: number;
  similarity_threshold?: number;
  final_size?: number;
  keyword_weight?: number;
  field_weights?: AdminDocRetrievalFieldWeights;
  reference?: AdminDocRetrievalReferenceFilter;
  thread_id?: string | null;
  resume?: UserConversationResume | null;
  /** Gửi khi đang ở chế độ soạn thảo trực tiếp (live); BE bỏ qua intent routing. */
  ui_template?: string;
};

export type UserConversationData = {
  status: "waiting_human" | "completed" | string;
  message?: string;
  answer?: string;
  query?: string;
  reference?: RetrievalReferenceItem[];
  thread_id?: string;
  hitl?: UserConversationHitl | null;
  resume?: UserConversationResume | null;
  answer_mode?: string;
  form_schema?: unknown;
  filled_values?: Record<string, unknown>;
  template_document_id?: string;
  draft_version?: number;
  draft_object_key?: string;
  draft_preview_markdown?: string;
  output?: Record<string, unknown>;
  ui_template?: string;
  chunk_total?: number;
  [key: string]: unknown;
};

const DEFAULT_FIELD_WEIGHTS: AdminDocRetrievalFieldWeights = {
  fields: [
    "article_title^8",
    "subject_title^6",
    "topic_title^5",
    "content_text^2",
  ],
};

function buildUserConversationBody(
  params: UserConversationRequest,
): Record<string, unknown> {
  const sessionId = params.session_id?.trim();
  const body: Record<string, unknown> = {
    query: params.query.trim(),
    stream: params.stream ?? true,
    candidate_size: params.candidate_size ?? 1,
    similarity_threshold: params.similarity_threshold ?? 0.6,
    final_size: params.final_size ?? 1,
    keyword_weight: params.keyword_weight ?? 0.2,
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
  const threadId = params.thread_id?.trim();
  if (threadId) {
    body.thread_id = threadId;
  }
  if (params.resume != null) {
    body.resume = params.resume;
  }
  const uiTemplate = params.ui_template?.trim();
  if (uiTemplate) {
    body.ui_template = uiTemplate;
  }
  return body;
}

/**
 * Gửi tin nhắn user chat qua orchestrator (POST /v1/user/user_chat).
 * Backend trả { code, msg, data: envelope orchestrator }.
 */
export const useUserConversation = () => {
  const {
    data,
    isPending: loading,
    isError,
    error,
    mutateAsync,
    reset,
  } = useMutation({
    mutationKey: ["chat", "userConversation"],
    mutationFn: async (
      params: UserConversationRequest,
    ): Promise<ApiEnvelope<UserConversationData>> => {
      const axiosResponse: AxiosResponse<ApiEnvelope<UserConversationData>> =
        await chatService.userConversation(buildUserConversationBody(params));
      return axiosResponse.data ?? { code: -1, msg: "Empty response" };
    },
  });

  return {
    data,
    loading,
    isError,
    error,
    converse: mutateAsync,
    reset,
  };
};
