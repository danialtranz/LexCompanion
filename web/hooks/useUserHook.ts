import { Authorization } from "@/constants/authoriztions";
import userService from "@/service/userService";
import authorizationUtil from "@/utils/authorizationUtil";
import { useMutation } from "@tanstack/react-query";
import { setToken } from "../utils/tokenManager";
//import { useHotToast } from "@/components/ui/hot-toast";
import { setUserId } from "@/utils/tokenManager";
import { useEffect, useState } from "react";
import { getToken } from "@/utils/tokenManager";
export const useSignInGoogle = () => {
  //const { error, success } = useHotToast();
  const {
    data,
    isPending: loading,
    mutateAsync,
  } = useMutation({
    mutationKey: ["oauth-login"],
    mutationFn: async (params: {
      code: string;
      google_redirect_uri: string;
    }) => {
      // console.log("[useSignInGoogle] Bắt đầu gọi API oauthLogin với params:", {
      //   code: params.code ? `${params.code.substring(0, 20)}...` : "empty",
      //   google_redirect_uri: params.google_redirect_uri,
      // });

      // console.log("[useSignInGoogle] Gọi userService.oauthLogin...");
      const axiosResponse = await userService.oauthLogin(params as any);
      const res = axiosResponse.data || {};
      const payload = res.data ?? {};

      if (res.code === 0) {
        // Axios normalizes response headers to lowercase
        const authorization =
          axiosResponse?.headers?.[Authorization] ||
          axiosResponse?.headers?.[Authorization.toLowerCase()] ||
          "";

        // API hiện tại: { token, role, avatar, user: { id, email, username, super_admin, ... } }
        // Legacy: { tokenInfo.token, id, username, email, picture, superAdmin }
        const token =
          payload.tokenInfo?.token ?? payload.token ?? "";
        const nestedUser = payload.user;
        const userIdRaw =
          nestedUser?.id ??
          payload.id ??
          "";
        const userId = String(userIdRaw).trim();

        if (!token) {
          throw new Error("OAuth response missing token");
        }

        setToken(token);
        setUserId(userId);

        const username = nestedUser?.username ?? payload.username ?? "";
        const email = nestedUser?.email ?? payload.email ?? "";
        const picture =
          payload.picture ?? payload.avatar ?? nestedUser?.picture ?? "";
        const isAdmin =
          nestedUser?.super_admin === true ||
          nestedUser?.super_admin === 1 ||
          payload.superAdmin === 1 ||
          payload.role === "super_admin" ||
          payload.role === "admin";

        const userInfo = {
          name: username,
          email,
          picture,
          id: userId,
          role: isAdmin ? "admin" : "user",
        };
        authorizationUtil.setItems({
          Authorization: authorization,
          userInfo: JSON.stringify(userInfo),
          Token: token,
        });
        //success({ key: "hooks.loginHook.success" });
        //console.log("[useSignInGoogle] Đã lưu thông tin vào authorizationUtil");
      } else {
        //console.log("[useSignInGoogle] Login thất bại với code:", res.code);
        //error({ key: "hooks.loginHook.error" });
      }
      return res.code;
    },
  });
  return { data, loading, login: mutateAsync };
};

export const useAuthTokenReady = (pollIntervalMs: number = 100): boolean => {
  const [ready, setReady] = useState<boolean>(() => {
    if (typeof window === "undefined") return false;
    return !!getToken();
  });

  useEffect(() => {
    // Nếu đã sẵn sàng thì không cần poll nữa
    if (ready) return;

    // Chỉ chạy trên client
    if (typeof window === "undefined") {
      return;
    }

    const id = setInterval(() => {
      if (getToken()) {
        setReady(true);
        clearInterval(id);
      }
    }, pollIntervalMs);

    return () => {
      clearInterval(id);
    };
  }, [pollIntervalMs, ready]);
  return ready;
};
