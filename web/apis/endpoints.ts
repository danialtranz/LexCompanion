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
};
export default api;
