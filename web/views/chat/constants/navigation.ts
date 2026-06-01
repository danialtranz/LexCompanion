export interface NavItem {
  id: string;
  label: string;
  href: string;
}

export const CHAT_NAV_ITEMS: NavItem[] = [
  { id: "chat", label: "Trò chuyện", href: "/chat" },
  { id: "legal-docs", label: "Tài liệu của tôi", href: "#" },
  { id: "history", label: "Lịch sử hội thoại", href: "#" },
  { id: "settings", label: "Cài đặt", href: "#" },
];
