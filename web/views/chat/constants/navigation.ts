export interface NavItem {
  id: string;
  labelKey: string;
  href: string;
}

export const CHAT_NAV_ITEMS: NavItem[] = [
  { id: "chat", labelKey: "chat.nav.chat", href: "/chat" },
  { id: "legal-docs", labelKey: "chat.nav.legalDocs", href: "#" },
  { id: "history", labelKey: "chat.nav.history", href: "#" },
  {
    id: "data-visualize",
    labelKey: "chat.nav.dataVisualize",
    href: "/data-visualization",
  },
  { id: "settings", labelKey: "chat.nav.settings", href: "#" },
];
