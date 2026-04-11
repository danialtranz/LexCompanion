import api from "@/apis/endpoints";
import registerNextServer from "../utils/registerServer";

const { oauthLoginUrl } = api;

const methods = {
  oauthLogin: {
    url: oauthLoginUrl,
    method: "post",
  },
} as const;

const userService = registerNextServer<keyof typeof methods>(methods as any);

export default userService;
