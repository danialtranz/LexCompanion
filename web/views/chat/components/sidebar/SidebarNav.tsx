import Link from "next/link";
import { useRouter } from "next/router";
import {
  BarChart3,
  Clock3,
  FileText,
  MessageCircle,
  Settings,
  type LucideIcon,
} from "lucide-react";
import { CHAT_NAV_ITEMS } from "../../constants/navigation";

const NAV_ICONS: Record<string, LucideIcon> = {
  chat: MessageCircle,
  "legal-docs": FileText,
  history: Clock3,
  "data-visualize": BarChart3,
  settings: Settings,
};

const navItemClass = (active: boolean) =>
  `flex h-11 w-full items-center gap-3 rounded-xl px-3.5 text-[13px] font-medium transition-colors ${
    active
      ? "bg-[#f5ebe0] text-[#9a6c2b] shadow-[inset_0_0_0_1px_#e8d5b8]"
      : "text-[#5c554d] hover:bg-[#faf5ec] hover:text-[#9a6c2b]"
  }`;

type SidebarNavProps = {
  onOpenKnowledgeBase?: () => void;
  onToggleHistory?: () => void;
  knowledgeBaseActive?: boolean;
  historyActive?: boolean;
};

export const SidebarNav = ({
  onOpenKnowledgeBase,
  onToggleHistory,
  knowledgeBaseActive = false,
  historyActive = false,
}: SidebarNavProps) => {
  const router = useRouter();

  return (
    <nav className="grid gap-1">
      {CHAT_NAV_ITEMS.map((item) => {
        const Icon = NAV_ICONS[item.id] ?? MessageCircle;
        const isRouteActive =
          item.href !== "#" &&
          (router.pathname === item.href ||
            router.asPath.split("?")[0] === item.href);
        const isActive =
          item.id === "legal-docs"
            ? knowledgeBaseActive
            : item.id === "history"
              ? historyActive
              : isRouteActive;

        if (item.id === "history" && onToggleHistory) {
          return (
            <button
              key={item.id}
              type="button"
              onClick={onToggleHistory}
              className={`${navItemClass(isActive)} border-0 bg-transparent text-left cursor-pointer`}
            >
              <Icon className="h-[18px] w-[18px] shrink-0" strokeWidth={1.75} />
              {item.label}
            </button>
          );
        }

        if (item.id === "legal-docs" && onOpenKnowledgeBase) {
          return (
            <button
              key={item.id}
              type="button"
              onClick={onOpenKnowledgeBase}
              className={`${navItemClass(isActive)} border-0 bg-transparent text-left cursor-pointer`}
            >
              <Icon className="h-[18px] w-[18px] shrink-0" strokeWidth={1.75} />
              {item.label}
            </button>
          );
        }

        return (
          <Link
            key={item.id}
            href={item.href}
            className={navItemClass(isActive)}
          >
            <Icon className="h-[18px] w-[18px] shrink-0" strokeWidth={1.75} />
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
};
