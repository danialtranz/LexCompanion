import api from "@/apis/endpoints";
import registerNextServer from "../utils/registerServer";

const {
  docUploadUrl,
  docsListUrl,
  docDetailUrl,
  docUploadViaUrl,
  docRunUrl,
  adminDocTopicUrl,
  adminDocSubjectUrl,
  adminDocArticlesUrl,
} = api;

const methods = {
  /** POST multipart; dùng native config: `{ params: { kb_id }, data: FormData }` */
  uploadDocument: {
    url: docUploadUrl,
    method: "post",
  },
  listDocuments: {
    url: docsListUrl,
    method: "get",
  },
  /** GET presigned access URL theo doc_id */
  getDocument: {
    url: docDetailUrl,
    method: "get",
  },
  deleteDocument: {
    url: docDetailUrl,
    method: "delete",
  },
  uploadDocumentViaUrl: {
    url: docUploadViaUrl,
    method: "post",
  },
  runDocument: {
    url: docRunUrl,
    method: "post",
  },
  listAdminLegalTopics: {
    url: adminDocTopicUrl,
    method: "get",
  },
  getAdminLegalTopicDetail: {
    url: adminDocTopicUrl,
    method: "get",
  },
  listAdminLegalSubjects: {
    url: adminDocSubjectUrl,
    method: "get",
  },
  getAdminLegalSubjectDetail: {
    url: adminDocSubjectUrl,
    method: "get",
  },
  listAdminLegalArticles: {
    url: adminDocArticlesUrl,
    method: "get",
  },
} as const;

const documentService = registerNextServer<keyof typeof methods>(
  methods as Record<keyof typeof methods, { url: string; method: string }>,
);

export default documentService;
