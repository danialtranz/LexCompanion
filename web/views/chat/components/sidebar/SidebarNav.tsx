import Link from "next/link";
import { useRouter } from "next/router";
import { CHAT_NAV_ITEMS } from "../../constants/navigation";

export const SidebarNav = () => {
  const router = useRouter();

  return (
    <nav className="grid gap-3">
      {CHAT_NAV_ITEMS.map((item) => {
        const isActive =
          item.href !== "#" &&
          (router.pathname === item.href ||
            router.asPath.split("?")[0] === item.href);

        return (
          <Link
            key={item.id}
            href={item.href}
            className={`flex h-[50px] items-center gap-2.5 rounded-[10px] px-3.5 text-[13px] transition-colors ${
              isActive
                ? "bg-gradient-to-r from-[#fff4df] to-[#fffaf2] text-[#9b6416] shadow-[inset_0_0_0_1px_#f1e2cb]"
                : "text-[#635d56] hover:bg-gradient-to-r hover:from-[#fff4df] hover:to-[#fffaf2] hover:text-[#9b6416] hover:shadow-[inset_0_0_0_1px_#f1e2cb]"
            }`}
          >
            <span aria-hidden>{item.icon}</span>
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
};
