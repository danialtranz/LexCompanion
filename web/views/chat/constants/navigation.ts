export interface NavItem {
  id: string;
  label: string;
  href: string;
}

export const CHAT_NAV_ITEMS: NavItem[] = [
  { id: "chat", label: "Trò chuyện", href: "/chat" },
  { id: "legal-docs", label: "Tài liệu của tôi", href: "#" },
  { id: "history", label: "Lịch sử hội thoại", href: "#" },
  {
    id: "data-visualize",
    label: "Trực quan hóa dữ liệu",
    href: "/data-visualization",
  },
  { id: "settings", label: "Cài đặt", href: "#" },
];
