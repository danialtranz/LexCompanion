import { Authorization } from "@/constants/authoriztions";
import authorizationUtil, { redirectToLogin } from "@/utils/authorizationUtil";
import axios, { AxiosError, AxiosResponse } from "axios";
import { convertTheKeysOfTheObjectToSnake } from "./commonUtils";
import { getToken, removeToken } from "../utils/tokenManager";
import { toast } from "../hooks/useToast";
import Cookies from "js-cookie";

const MESSAGE_BY_CODE = {
  200: "Success",
  201: "Created",
  202: "Accepted",
  204: "No Content",
  400: "Bad Request",
  401: "Unauthorized",
  403: "Forbidden",
  404: "Not Found",
  406: "Not Acceptable",
  410: "Gone",
  413: "Payload Too Large",
  422: "Unprocessable Entity",
  500: "Internal Server Error",
  502: "Bad Gateway",
  503: "Service Unavailable",
  504: "Gateway Timeout",
} as const;

const STATIC_MESSAGES = {
  authenticationError: "Authentication Error",
  networkAnomaly: "Network Error",
  networkAnomalyDescription:
    "Unable to connect to the server. Please check your network connection or ensure the server is running.",
  timeoutError: "Request Timeout",
  timeoutErrorDescription:
    "The request took too long to complete. Please try again later.",
  serverError: "Server Error",
  criticalError: "Critical Error",
  unknownCriticalError:
    "An unexpected critical error occurred. Please try again later.",
} as const;

export const RetcodeMessage = {
  200: MESSAGE_BY_CODE[200],
  201: MESSAGE_BY_CODE[201],
  202: MESSAGE_BY_CODE[202],
  204: MESSAGE_BY_CODE[204],
  400: MESSAGE_BY_CODE[400],
  401: MESSAGE_BY_CODE[401],
  403: MESSAGE_BY_CODE[403],
  404: MESSAGE_BY_CODE[404],
  406: MESSAGE_BY_CODE[406],
  410: MESSAGE_BY_CODE[410],
  413: MESSAGE_BY_CODE[413],
  422: MESSAGE_BY_CODE[422],
  500: MESSAGE_BY_CODE[500],
  502: MESSAGE_BY_CODE[502],
  503: MESSAGE_BY_CODE[503],
  504: MESSAGE_BY_CODE[504],
};
export type ResultCode =
  | 200
  | 201
  | 202
  | 204
  | 400
  | 401
  | 403
  | 404
  | 406
  | 410
  | 413
  | 422
  | 500
  | 502
  | 503
  | 504;

/**
 * Kiểm tra xem có phải lỗi nghiêm trọng (network/server) không
 * Các lỗi nghiêm trọng cần được handle ở đây với Radix toast
 */
const isCriticalError = (error: AxiosError | Error): boolean => {
  // Axios error có code
  if ("code" in error) {
    const code = (error as AxiosError).code;
    // Network errors
    if (
      code === "ERR_NETWORK" ||
      code === "ECONNREFUSED" ||
      code === "ETIMEDOUT" ||
      code === "ENOTFOUND" ||
      code === "ECONNABORTED"
    ) {
      return true;
    }
  }

  // Kiểm tra message
  const message = error.message || "";
  //console.log(">>>>>> message: ", message);
  if (
    message.includes("Network Error") ||
    message.includes("Failed to fetch") ||
    message.includes("ERR_NETWORK") ||
    message.includes("ECONNREFUSED") ||
    message.includes("timeout")
  ) {
    return true;
  }

  // Axios error: có request nhưng không có response = server không phản hồi
  const axiosError = error as AxiosError;
  if (axiosError.request && !axiosError.response) {
    return true;
  }

  // Server errors (5xx) - nghiêm trọng
  if (axiosError.response) {
    const status = axiosError.response.status;
    if (status >= 500 && status < 600) {
      return true;
    }
  }

  return false;
};

const clearAllAuthData = (): void => {
  // 1. Xóa token sử dụng hàm removeToken() đã được cải thiện
  removeToken();

  // 2. Xóa các key authorization khác
  authorizationUtil.removeAll();

  // 3. Xóa tất cả localStorage (trừ userLanguage)
  if (typeof window !== "undefined") {
    const keysToKeep = ["userLanguage", "lng"]; // Giữ lại các key cần thiết
    Object.keys(localStorage).forEach((key) => {
      if (!keysToKeep.includes(key)) {
        localStorage.removeItem(key);
      }
    });
  }

  // 4. Xóa tất cả cookies với tất cả các options
  if (typeof window !== "undefined") {
    const allCookies = Cookies.get();
    const hostname = window.location.hostname;

    Object.keys(allCookies).forEach((cookieName) => {
      // Xóa với path: "/"
      Cookies.remove(cookieName, { path: "/" });

      // Xóa với domain nếu không phải localhost
      if (
        hostname &&
        !hostname.startsWith("localhost") &&
        !hostname.startsWith("127.0.0.1")
      ) {
        Cookies.remove(cookieName, { path: "/", domain: hostname });
        Cookies.remove(cookieName, { path: "/", domain: `.${hostname}` });
      }
    });
  }
};
/**
 * Error handler cho các lỗi nghiêm trọng (network/server)
 * Chỉ handle các lỗi nghiêm trọng ở đây, các lỗi đơn giản (400, 422) để hook handle
 */
const errorHandler = (error: AxiosError | Error): AxiosResponse | undefined => {
  const axiosError = error as AxiosError;
  if (axiosError.response) {
    const status = axiosError.response.status;
    if (status === 401 || status === 403) {
      const errorText =
        RetcodeMessage[status as ResultCode] ||
        axiosError.response.statusText ||
        "Unauthorized";

      toast({
        title: `${STATIC_MESSAGES.authenticationError} ${status}`,
        description: errorText,
        variant: "destructive",
      });

      // Xóa tất cả auth data ngay lập tức
      clearAllAuthData();

      // Tự động redirect sau 2 giây
      setTimeout(() => {
        redirectToLogin();
      }, 2000);

      return axiosError.response;
    }
  }
  // Chỉ handle các lỗi nghiêm trọng ở đây
  if (!isCriticalError(error)) {
    // Không phải lỗi nghiêm trọng -> để hook handle
    return axiosError.response;
  }

  // ========== XỬ LÝ CÁC LỖI NGHIÊM TRỌNG ==========

  // 1. Network Error - Server chưa bật, mất mạng, không kết nối được
  if (
    axiosError.code === "ERR_NETWORK" ||
    axiosError.code === "ECONNREFUSED" ||
    axiosError.code === "ENOTFOUND" ||
    (axiosError.request && !axiosError.response) ||
    error.message?.includes("Network Error") ||
    error.message?.includes("Failed to fetch")
  ) {
    toast({
      title: STATIC_MESSAGES.networkAnomaly,
      description: STATIC_MESSAGES.networkAnomalyDescription,
      variant: "destructive",
    });
    return undefined;
  }

  // 2. Timeout Error
  if (
    axiosError.code === "ETIMEDOUT" ||
    axiosError.code === "ECONNABORTED" ||
    error.message?.includes("timeout")
  ) {
    toast({
      title: STATIC_MESSAGES.timeoutError,
      description: STATIC_MESSAGES.timeoutErrorDescription,
      variant: "destructive",
    });
    return undefined;
  }

  // 3. Server Errors (5xx) - Server bị lỗi
  if (axiosError.response) {
    const status = axiosError.response.status;
    if (status >= 500 && status < 600) {
      const errorText =
        RetcodeMessage[status as ResultCode] ||
        axiosError.response.statusText ||
        "Internal Server Error";

      toast({
        title: `${STATIC_MESSAGES.serverError} ${status}`,
        description: errorText,
        variant: "destructive",
      });
      return axiosError.response;
    }

    // 4. Authentication/Authorization Errors (401, 403) - Nghiêm trọng, cần redirect
    if (status === 401 || status === 403) {
      const errorText =
        RetcodeMessage[status as ResultCode] ||
        axiosError.response.statusText ||
        "Unauthorized";

      toast({
        title: `${STATIC_MESSAGES.authenticationError} ${status}`,
        description: errorText,
        variant: "destructive",
      });

      // Tự động redirect sau 2 giây
      clearAllAuthData();
      setTimeout(() => {
        redirectToLogin();
      }, 2000);

      return axiosError.response;
    }
  }

  // Fallback cho các lỗi nghiêm trọng khác
  toast({
    title: STATIC_MESSAGES.criticalError,
    description:
      error.message || STATIC_MESSAGES.unknownCriticalError,
    variant: "destructive",
  });

  return axiosError.response;
};

const request = axios.create({
  //   errorHandler,
  timeout: 300000,
  //   getResponse: true,
});

request.interceptors.request.use(
  (config) => {
    // Skip conversion for FormData - giữ nguyên FormData để gửi file
    const isFormData = config.data instanceof FormData;
    //console.log(">>>>>> isFormData123: ", config.data);
    // Nếu là FormData, không xử lý gì cả - giữ nguyên config và chỉ thêm token
    if (isFormData) {
      //console.log(">>>>>> isFormData: ", config);
      // Chỉ modify headers để thêm token, giữ nguyên data (FormData)
      const skipToken = (config as { skipToken?: boolean }).skipToken;
      if (!skipToken) {
        const token = getToken();
        if (token) {
          if (!config.headers) {
            config.headers = {} as typeof config.headers;
          }
          (config.headers as Record<string, string>)[Authorization] =
            `Bearer ${token}`;
        }
      }

      // Return config gốc, chỉ modify headers
      return config;
    }

    // Xử lý bình thường cho các request không phải FormData
    const data = convertTheKeysOfTheObjectToSnake(config.data);
    const params = convertTheKeysOfTheObjectToSnake(config.params);
    const newConfig = { ...config, data, params };

    const skipToken = (config as { skipToken?: boolean }).skipToken;
    if (!skipToken) {
      const token = getToken();
      if (token) {
        if (!newConfig.headers) {
          newConfig.headers = {} as typeof newConfig.headers;
        }
        (newConfig.headers as Record<string, string>)[Authorization] =
          `Bearer ${token}`;
      }
    }
    // in ra config.headers
    //console.log(">>>>>> config.headers:", newConfig.headers);
    return newConfig;
  },
  function (error) {
    return Promise.reject(error);
  },
);

request.interceptors.response.use(
  async (response) => {
    // Chỉ handle các lỗi nghiêm trọng ở đây
    // Các lỗi đơn giản (400, 422, data.code !== 0) để hook handle

    // 1. Lỗi nghiêm trọng về kích thước/timeout (413, 504)
    if (response?.status === 413 || response?.status === 504) {
      toast({
        title: RetcodeMessage[response?.status as ResultCode] || "Error",
        variant: "destructive",
      });
    }

    if (response.config.responseType === "blob") {
      return response;
    }

    const data = response?.data;

    // 2. Authentication error từ response data (nghiêm trọng - cần redirect)
    if (data && (data.code === 401 || data.code === 403)) {
      const status = data.code as 401 | 403;
      const errorText =
        RetcodeMessage[status as ResultCode] || data.msg || "Unauthorized";

      toast({
        title: `${STATIC_MESSAGES.authenticationError} ${status}`,
        description: errorText,
        variant: "destructive",
      });

      // Xóa toàn bộ dữ liệu auth và redirect về login
      clearAllAuthData();
      setTimeout(() => {
        redirectToLogin();
      }, 2000);

      // Reject để các hook phía trên có thể handle nếu cần
      return Promise.reject(response);
    }
    // Các lỗi khác (data.code === 100, data.code !== 0) là lỗi đơn giản
    // -> Để hook handle, không show toast ở đây

    return response;
  },
  function (error: AxiosError | Error) {
    //console.log("🚀 ~ error:", error);
    // Handle critical errors (network, server errors)
    errorHandler(error);
    // Luôn reject để hook có thể handle thêm nếu cần
    return Promise.reject(error);
  },
);

export default request;

export const get = (url: string) => {
  return request.get(url);
};

export const post = (url: string, body: Record<string, unknown>) => {
  return request.post(url, { data: body });
};

export const drop = () => {};

export const put = () => {};
