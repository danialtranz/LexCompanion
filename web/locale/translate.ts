import i18n from "./i18n";

/** Dùng trong util/hook không có React context. */
export function translate(
  key: string,
  options?: Record<string, unknown>,
): string {
  return i18n.t(key, options ?? {});
}
