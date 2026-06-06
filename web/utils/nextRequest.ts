import { Authorization } from "@/constants/authoriztions";
import authorizationUtil, { redirectToLogin } from "@/utils/authorizationUtil";
import axios, { AxiosError, AxiosResponse } from "axios";
import Cookies from "js-cookie";
import { convertTheKeysOfTheObjectToSnake } from "./commonUtils";
import { getToken, removeToken } from "../utils/tokenManager";
import { toast } from "../hooks/useToast";

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

const isCriticalError = (error: AxiosError | Error): boolean => {
  if ("code" in error) {
    const code = (error as AxiosError).code;
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

  const message = error.message || "";
  if (
    message.includes("Network Error") ||
    message.includes("Failed to fetch") ||
    message.includes("ERR_NETWORK") ||
    message.includes("ECONNREFUSED") ||
    message.includes("timeout")
  ) {
    return true;
  }

  const axiosError = error as AxiosError;
  if (axiosError.request && !axiosError.response) {
    return true;
  }

  if (axiosError.response) {
    const status = axiosError.response.status;
    if (status >= 500 && status < 600) {
      return true;
    }
  }

  return false;
};

const clearAllAuthData = (): void => {
  removeToken();
  authorizationUtil.removeAll();

  if (typeof window !== "undefined") {
    const keysToKeep = ["userLanguage", "lng"];
    Object.keys(localStorage).forEach((key) => {
      if (!keysToKeep.includes(key)) {
        localStorage.removeItem(key);
      }
    });
  }

  if (typeof window !== "undefined") {
    const allCookies = Cookies.get();
    const hostname = window.location.hostname;

    Object.keys(allCookies).forEach((cookieName) => {
      Cookies.remove(cookieName, { path: "/" });

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

      clearAllAuthData();

      setTimeout(() => {
        redirectToLogin();
      }, 2000);

      return axiosError.response;
    }
  }

  if (!isCriticalError(error)) {
    return axiosError.response;
  }

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

      clearAllAuthData();
      setTimeout(() => {
        redirectToLogin();
      }, 2000);

      return axiosError.response;
    }
  }

  toast({
    title: STATIC_MESSAGES.criticalError,
    description: error.message || STATIC_MESSAGES.unknownCriticalError,
    variant: "destructive",
  });

  return axiosError.response;
};

const request = axios.create({
  timeout: 300000,
});

request.interceptors.request.use(
  (config) => {
    const isFormData = config.data instanceof FormData;

    if (isFormData) {
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

      return config;
    }

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

    return newConfig;
  },
  function (error) {
    return Promise.reject(error);
  },
);

request.interceptors.response.use(
  async (response) => {
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

    if (data && (data.code === 401 || data.code === 403)) {
      const status = data.code as 401 | 403;
      const errorText =
        RetcodeMessage[status as ResultCode] || data.msg || "Unauthorized";

      toast({
        title: `${STATIC_MESSAGES.authenticationError} ${status}`,
        description: errorText,
        variant: "destructive",
      });

      clearAllAuthData();
      setTimeout(() => {
        redirectToLogin();
      }, 2000);

      return Promise.reject(response);
    }

    return response;
  },
  function (error: AxiosError | Error) {
    errorHandler(error);
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
