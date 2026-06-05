const api_host = `${process.env.NEXT_PUBLIC_API_SERVER}`;

export { api_host };

const api = {
  // user
  oauthLoginUrl: `${api_host}/v1/user/oAuth-login`,
  // documents (FastAPI prefix /v1)
  docUploadUrl: `${api_host}/v1/doc/upload`,
  docsListUrl: `${api_host}/v1/docs`,
  docDetailUrl: `${api_host}/v1/doc`,
  /** GET blob qua API (JWT), cùng host với API */
  docContentUrl: `${api_host}/v1/doc/content`,
  docUploadViaUrl: `${api_host}/v1/doc/upload_via_url`,
  docRunUrl: `${api_host}/v1/doc/run`,
  // admin legal corpus
  adminDocTopicUrl: `${api_host}/v1/admin/doc/topic`,
  adminDocSubjectUrl: `${api_host}/v1/admin/doc/subject`,
  adminDocArticlesUrl: `${api_host}/v1/admin/doc/articles`,
  /** POST — tra cứu pháp điển (search → rerank → LLM) */
  adminDocRetrievalUrl: `${api_host}/v1/admin/doc/retrieval`,
  /** User chat sessions */
  userChatUrl: `${api_host}/v1/user/chat`,
  /** POST — orchestrated user chat (intent + LangGraph task_execution) */
  userUserChatUrl: `${api_host}/v1/user/user_chat`,
  userChatSessionsUrl: `${api_host}/v1/user/sessions`,
  userChatSessionUrl: `${api_host}/v1/user/session`,
  /** POST multipart — user upload file (PDF/DOCX/ảnh) gắn session tùy chọn */
  userUploadUrl: `${api_host}/v1/user/upload`,
  /** GET — markdown preview bản nháp đã điền (theo session) */
  userContractDraftPreviewUrl: `${api_host}/v1/user/contract/draft/preview`,
  /** GET — HTML preview từ DOCX nháp MinIO (theo session) */
  userContractDraftPreviewHtmlUrl: `${api_host}/v1/user/contract/draft/preview/html`,
  /** GET — DOCX nháp binary từ MinIO (inline, FE render trực tiếp) */
  userContractDraftPreviewBinaryUrl: `${api_host}/v1/user/contract/draft/preview/binary`,
  userContractDraftVersionsUrl: `${api_host}/v1/user/contract/draft/versions`,
  userContractDraftDownloadUrl: `${api_host}/v1/user/contract/draft`,
};
export default api;
