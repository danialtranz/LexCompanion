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
    content:
      "Thủ tục thành lập công ty TNHH 2 thành viên trở lên được quy định tại Luật Doanh nghiệp 2020. Quy trình cơ bản gồm: (1) Chuẩn bị hồ sơ đăng ký doanh nghiệp; (2) Nộp hồ sơ tại Phòng Đăng ký kinh doanh; (3) Nhận Giấy chứng nhận đăng ký doanh nghiệp; (4) Khắc dấu và công bố thông tin doanh nghiệp; (5) Mở tài khoản ngân hàng và thông báo tài khoản.\n\nBạn cần tôi giải thích chi tiết bước nào không?",
    time: "10:31",
    citations: [
      {
        id: "c1",
        index: 1,
        title: "Luật Doanh nghiệp 2020",
        meta: "Chương III · Điều 46",
        href: "#",
        excerpt:
          "Công ty trách nhiệm hữu hạn hai thành viên trở lên là công ty có từ 02 thành viên trở lên, tối đa không quá 50 thành viên là tổ chức, cá nhân; thành viên chịu trách nhiệm về các khoản nợ và các nghĩa vụ tài sản khác của doanh nghiệp trong phạm vi số vốn góp vào doanh nghiệp.",
      },
      {
        id: "c2",
        index: 2,
        title: "Luật Doanh nghiệp 2020",
        meta: "Chương III · Điều 47",
        href: "#",
        excerpt:
          "Công ty trách nhiệm hữu hạn hai thành viên trở lên có tư cách pháp nhân kể từ ngày được cấp Giấy chứng nhận đăng ký doanh nghiệp.",
      },
      {
        id: "c3",
        index: 3,
        title: "Nghị định 01/2021/NĐ-CP",
        meta: "Điều 12 · Hồ sơ đăng ký doanh nghiệp",
        href: "#",
        excerpt:
          "Hồ sơ đăng ký thành lập doanh nghiệp gồm: Giấy đề nghị đăng ký doanh nghiệp; Điều lệ công ty; Danh sách thành viên; Bản sao giấy tờ pháp lý của thành viên; Giấy ủy quyền (nếu có).",
      },
    ],
  },
];
