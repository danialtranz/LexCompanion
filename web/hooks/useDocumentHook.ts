import documentService from "@/service/documentService";
import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import type { AxiosResponse } from "axios";

/** Body JSON từ backend ({ code, msg, data }) */
export type ApiEnvelope<T = unknown> = {
  code: number;
  msg?: string;
  data?: T;
};

export type DocumentListItem = {
  id: string;
  kb_id: string;
  file_id: string;
  name: string;
  type: string;
  suffix: string;
  size: number;
  token_num: number;
  chunk_num: number;
  progress: number;
  process_duration: number;
  content_hash: string | null;
  source_type: string;
  location: string;
  created_by: string;
  run: string;
  status: string;
  create_date: string | null;
  update_date: string | null;
  has_thumbnail?: boolean;
};

export type DocumentListData = {
  kb_id: string;
  total: number;
  page: number;
  page_size: number;
  items: DocumentListItem[];
};

export type UploadDocumentData = {
  document_id: string;
  file_id: string;
  kb_id: string;
  tenant_id: string;
  name: string;
  size: number;
  type: string;
  suffix: string;
  object_key: string;
  location: string;
  access_url: string;
  /** GET /v1/doc/content?doc_id=… (Authorization Bearer) — trả blob từ MinIO qua API */
  content_url?: string;
  etag?: string | null;
  bucket_mode?: string;
  content_hash?: string | null;
  has_thumbnail?: boolean;
};

export type DocumentAccessData = {
  document_id: string;
  file_id: string;
  access_url: string;
  content_url?: string;
  expires_in_seconds: number;
  object_key: string;
  tenant_id: string;
};

export type DocListQueryParams = {
  kb_id?: string | null;
  page?: number;
  page_size?: number;
};

function normalizeKbQuery(kb_id: string | null | undefined): string {
  if (kb_id === undefined || kb_id === null) return "null";
  const s = String(kb_id).trim();
  if (s === "") return "null";
  return s;
}

const QK = {
  list: (kb: string, page: number, pageSize: number) =>
    ["documents", "list", kb, page, pageSize] as const,
  access: (docId: string) => ["documents", "access", docId] as const,
};

/**
 * Upload một file vào KB (multipart form field `file`).
 * Backend trả code 201 khi thành công.
 */
export const useUploadDocument = () => {
  const queryClient = useQueryClient();
  const {
    data,
    isPending: loading,
    mutateAsync,
  } = useMutation({
    mutationKey: ["document", "upload"],
    mutationFn: async (params: {
      file: File;
      kb_id?: string | null;
    }): Promise<ApiEnvelope<UploadDocumentData>> => {
      const formData = new FormData();
      formData.append("file", params.file);
      const kbQ = normalizeKbQuery(params.kb_id);
      const axiosResponse: AxiosResponse<ApiEnvelope<UploadDocumentData>> =
        await documentService.uploadDocument(
          {
            params: { kb_id: kbQ },
            data: formData,
          },
          true,
        );
      const res = axiosResponse.data ?? ({} as ApiEnvelope<UploadDocumentData>);
      if (res.code === 201 || res.code === 0) {
        queryClient.invalidateQueries({ queryKey: ["documents", "list"] });
      }
      return res;
    },
  });
  return { data, loading, upload: mutateAsync };
};

/**
 * Danh sách tài liệu theo KB (phân trang).
 */
export const useDocumentsList = (params: DocListQueryParams) => {
  const page = params.page ?? 1;
  const page_size = params.page_size ?? 5;
  const kbQ = normalizeKbQuery(params.kb_id);

  return useQuery({
    queryKey: QK.list(kbQ, page, page_size),
    placeholderData: keepPreviousData,
    queryFn: async (): Promise<ApiEnvelope<DocumentListData>> => {
      const axiosResponse = await documentService.listDocuments(
        {
          params: { kb_id: kbQ, page, page_size },
        },
        true,
      );
      return axiosResponse.data ?? { code: -1, msg: "Empty response" };
    },
  });
};

/**
 * Lấy presigned URL truy cập file theo doc_id.
 */
export const useDocumentAccess = (
  docId: string | undefined,
  options?: { enabled?: boolean },
) => {
  const enabled = (options?.enabled ?? true) && !!docId;

  return useQuery({
    queryKey: QK.access(docId ?? ""),
    queryFn: async (): Promise<ApiEnvelope<DocumentAccessData>> => {
      const axiosResponse = await documentService.getDocument(
        {
          params: { doc_id: docId! },
        },
        true,
      );
      return axiosResponse.data ?? { code: -1, msg: "Empty response" };
    },
    enabled,
  });
};

/**
 * Xóa mềm document theo doc_id.
 */
export const useDeleteDocument = () => {
  const queryClient = useQueryClient();
  const {
    data,
    isPending: loading,
    mutateAsync,
  } = useMutation({
    mutationKey: ["document", "delete"],
    mutationFn: async (doc_id: string): Promise<number> => {
      const axiosResponse = await documentService.deleteDocument(
        {
          params: { doc_id },
        },
        true,
      );
      const res = axiosResponse.data ?? ({} as ApiEnvelope);
      if (res.code === 0) {
        queryClient.invalidateQueries({ queryKey: ["documents", "list"] });
        queryClient.removeQueries({ queryKey: QK.access(doc_id) });
      }
      return res.code;
    },
  });
  return { data, loading, deleteDocument: mutateAsync };
};

export const useUploadDocumentViaUrl = () => {
  const queryClient = useQueryClient();
  const {
    data,
    isPending: loading,
    mutateAsync,
  } = useMutation({
    mutationKey: ["document", "uploadViaUrl"],
    mutationFn: async (params: {
      url: string;
      doc_name: string | null;
      kb_id?: string | null;
    }): Promise<ApiEnvelope<UploadDocumentData>> => {
      const axiosResponse = await documentService.uploadDocumentViaUrl(
        {
          params: { kb_id: normalizeKbQuery(params.kb_id) },
          data: {
            url_scraping: params.url,
            doc_name: params.doc_name,
          },
        },
        true,
      );
      // refetch lai ds documents
      queryClient.invalidateQueries({ queryKey: ["documents", "list"] });
      return axiosResponse.data ?? { code: -1, msg: "Empty response" };
    },
  });
  return { data, loading, uploadDocumentViaUrl: mutateAsync };
};

export const useRunDocument = () => {
  return useMutation({
    mutationKey: ["document", "run"],
    mutationFn: async (doc_id: string): Promise<ApiEnvelope<void>> => {
      const axiosResponse = await documentService.runDocument(
        {
          params: { doc_id },
        },
        true,
      );
      return axiosResponse.data ?? { code: -1, msg: "Empty response" };
    },
  });
};
