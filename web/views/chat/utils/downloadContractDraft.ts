import api from "@/apis/endpoints";
import { getToken } from "@/utils/tokenManager";

/**
 * Tải DOCX nháp qua GET /v1/user/contract/draft (có JWT).
 */
export async function downloadContractDraft(params: {
  sessionId: string;
  version?: number;
}): Promise<void> {
  const token = getToken();
  if (!token) throw new Error("Chưa đăng nhập");

  const search = new URLSearchParams({ session_id: params.sessionId });
  if (params.version != null && params.version > 0) {
    search.set("version", String(params.version));
  }

  const res = await fetch(`${api.userContractDraftDownloadUrl}?${search}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Không tải được bản nháp");

  const blob = await res.blob();
  const disposition = res.headers.get("Content-Disposition") ?? "";
  const match = disposition.match(/filename="([^"]+)"/);
  const filename = match?.[1] ?? `hop_dong_da_dien_v${params.version ?? "latest"}.docx`;

  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}
