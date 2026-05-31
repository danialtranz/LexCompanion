import type { ChatMessage } from "../types";

export const MOCK_CONVERSATION: ChatMessage[] = [
  {
    id: "user-1",
    type: "user",
    content:
      "Thủ tục thành lập công ty TNHH 2 thành viên trở lên được quy định như thế nào?",
    time: "10:30",
  },
  {
    id: "bot-1",
    type: "bot",
    intro:
      "Thủ tục thành lập công ty TNHH 2 thành viên trở lên được quy định tại Luật Doanh nghiệp 2020. Quy trình cơ bản gồm các bước sau:",
    steps: [
      "Chuẩn bị hồ sơ đăng ký doanh nghiệp",
      "Nộp hồ sơ tại Phòng Đăng ký kinh doanh",
      "Nhận Giấy chứng nhận đăng ký doanh nghiệp",
      "Khắc dấu và công bố thông tin doanh nghiệp",
      "Mở tài khoản ngân hàng và thông báo tài khoản",
    ],
    outro: "Bạn cần tôi giải thích chi tiết bước nào không?",
    time: "10:31",
    sources: [
      { id: "s1", title: "Luật Doanh nghiệp 2020", href: "#" },
      { id: "s2", title: "Nghị định 01/2021/NĐ-CP", href: "#" },
    ],
  },
];
