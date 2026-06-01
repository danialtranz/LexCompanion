import Link from "next/link";
import { useRouter } from "next/router";
import {
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
  settings: Settings,
};

export const SidebarNav = () => {
  const router = useRouter();

  return (
    <nav className="grid gap-1">
      {CHAT_NAV_ITEMS.map((item) => {
        const Icon = NAV_ICONS[item.id] ?? MessageCircle;
        const isActive =
          item.href !== "#" &&
          (router.pathname === item.href ||
            router.asPath.split("?")[0] === item.href);

        return (
          <Link
            key={item.id}
            href={item.href}
            className={`flex h-11 items-center gap-3 rounded-xl px-3.5 text-[13px] font-medium transition-colors ${
              isActive
                ? "bg-[#f5ebe0] text-[#9a6c2b] shadow-[inset_0_0_0_1px_#e8d5b8]"
                : "text-[#5c554d] hover:bg-[#faf5ec] hover:text-[#9a6c2b]"
            }`}
          >
            <Icon className="h-[18px] w-[18px] shrink-0" strokeWidth={1.75} />
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
};
