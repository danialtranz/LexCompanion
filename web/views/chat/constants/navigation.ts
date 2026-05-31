export interface NavItem {
  id: string;
  label: string;
  icon: string;
  href: string;
}

export const CHAT_NAV_ITEMS: NavItem[] = [
  { id: "chat", label: "Trò chuyện", icon: "💬", href: "/chat" },
  {
    id: "knowledge-base",
    label: "Knowledge Base",
    icon: "📄",
    href: "/admin-knowledge-base",
  },
  { id: "legal-docs", label: "Văn bản pháp luật", icon: "📋", href: "#" },
  { id: "faq", label: "Hỏi đáp thường gặp", icon: "❔", href: "#" },
  { id: "history", label: "Lịch sử hội thoại", icon: "🕘", href: "#" },
  { id: "legal-services", label: "Dịch vụ pháp lý", icon: "⚙", href: "#" },
  { id: "settings", label: "Cài đặt", icon: "⚙", href: "#" },
];
