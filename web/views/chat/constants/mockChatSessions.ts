import type { MessageHistoryItem } from "../components/ChatHistory/types";

/** Dữ liệu mẫu khi API chưa có phiên — khớp mockup UI */
export const MOCK_CHAT_SESSIONS: MessageHistoryItem[] = [
  {
    id: "mock-1",
    title: "Thủ tục thành lập công ty TNHH 2 thành viên...",
    snippet:
      "Thủ tục thành lập công ty TNHH 2 thành viên trở lên được quy định tại Luật Doanh nghiệp 2020...",
    updatedAt: new Date().toISOString(),
  },
  {
    id: "mock-2",
    title: "Quyền và nghĩa vụ của người lao động",
    snippet: "Người lao động có quyền làm việc, hưởng lương và bảo hộ lao động...",
    updatedAt: new Date(Date.now() - 86_400_000).toISOString(),
  },
  {
    id: "mock-3",
    title: "Thủ tục đăng ký kết hôn tại UBND",
    snippet: "Hồ sơ đăng ký kết hôn gồm tờ khai, giấy tờ tùy thân và xác nhận tình trạng hôn nhân...",
    updatedAt: "2024-05-12T10:30:00.000Z",
  },
  {
    id: "mock-4",
    title: "Điều kiện cấp Giấy phép kinh doanh",
    snippet: "Doanh nghiệp phải đáp ứng điều kiện về ngành nghề, vốn pháp định và cơ sở vật chất...",
    updatedAt: "2024-05-10T14:20:00.000Z",
  },
];
