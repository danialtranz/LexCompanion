import i18n from "@/locale/i18n";
import { translate as t } from "@/locale/translate";

/** Hiển thị thời gian cho thẻ lịch sử: 10:30, Hôm qua, hoặc dd/MM/yyyy */
export function formatHistoryTimestamp(
  iso: string | null | undefined,
  now = new Date(),
): string {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";

  const startOfToday = new Date(now);
  startOfToday.setHours(0, 0, 0, 0);

  const startOfDate = new Date(date);
  startOfDate.setHours(0, 0, 0, 0);

  const diffDays = Math.round(
    (startOfToday.getTime() - startOfDate.getTime()) / 86_400_000,
  );

  const locale = i18n.language?.startsWith("en") ? "en-US" : "vi-VN";

  if (diffDays === 0) {
    return date.toLocaleTimeString(locale, {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });
  }
  if (diffDays === 1) return t("chat.history.yesterday");
  if (diffDays < 7) {
    return date.toLocaleDateString(locale, { weekday: "short" });
  }
  return date.toLocaleDateString(locale, {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}
