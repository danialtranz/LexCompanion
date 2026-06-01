import api from "@/apis/endpoints";
import registerNextServer from "../utils/registerServer";

const {
  adminDocRetrievalUrl,
  userChatUrl,
  userChatSessionsUrl,
  userChatSessionUrl,
} = api;

const methods = {
  /** POST /v1/admin/doc/retrieval — body JSON */
  adminDocRetrieval: {
    url: adminDocRetrievalUrl,
    method: "post",
  },
  /** DELETE /v1/user/chat?session_id=… */
  deleteUserChatSession: {
    url: userChatUrl,
    method: "delete",
  },
  /** GET /v1/user/sessions?page=&page_size= */
  listUserChatSessions: {
    url: userChatSessionsUrl,
    method: "get",
  },
  /** GET /v1/user/session?session_id=… */
  getUserChatSession: {
    url: userChatSessionUrl,
    method: "get",
  },
} as const;

const chatService = registerNextServer<keyof typeof methods>(
  methods as Record<keyof typeof methods, { url: string; method: string }>,
);

export default chatService;
