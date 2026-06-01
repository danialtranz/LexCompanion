import api from "@/apis/endpoints";
import registerNextServer from "../utils/registerServer";

const { adminDocRetrievalUrl } = api;

const methods = {
  /** POST /v1/admin/doc/retrieval — body JSON */
  adminDocRetrieval: {
    url: adminDocRetrievalUrl,
    method: "post",
  },
} as const;

const chatService = registerNextServer<keyof typeof methods>(
  methods as Record<keyof typeof methods, { url: string; method: string }>,
);

export default chatService;
