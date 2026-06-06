import { AxiosRequestConfig, AxiosResponse } from "axios";
import { isObject } from "lodash";
import request from "./nextRequest";

export default function registerNextServer<T extends string>(
  requestRecord: Record<
    T,
    { url: string | ((...args: Array<any>) => string); method: string }
  >,
) {
  type Server = Record<
    T,
    (
      config?:
        | AxiosRequestConfig<any>
        | Record<string, any>
        | string
        | number
        | boolean
        | undefined,
      useAxiosNativeConfig?: boolean,
    ) => Promise<AxiosResponse<any, any>>
  >;

  const server: Server = {} as Server;

  for (const name in requestRecord) {
    if (Object.prototype.hasOwnProperty.call(requestRecord, name)) {
      const { url, method } = requestRecord[name];
      server[name] = (config, useAxiosNativeConfig = false) => {
        const nextConfig = useAxiosNativeConfig ? config : { data: config };
        const finalConfig = isObject(nextConfig) ? nextConfig : {};
        const nextUrl = typeof url === "function" ? url(config) : url;
        return request({ url: nextUrl, method, ...finalConfig });
      };
    }
  }

  return server;
}
