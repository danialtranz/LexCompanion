import { Plus } from "lucide-react";
import { SidebarBrand } from "./SidebarBrand";
import { SidebarNav } from "./SidebarNav";
import { SidebarUpgrade } from "./SidebarUpgrade";
import { SidebarUser } from "./SidebarUser";

export const ChatSidebar = () => (
  <aside className="hidden min-h-screen w-[240px] shrink-0 flex-col border-r border-[#ebe3d6] bg-[#fffdf9] px-4 pb-5 pt-6 lg:flex">
    <SidebarBrand />

    <button
      type="button"
      className="mb-6 flex h-11 w-full items-center justify-center gap-2 rounded-xl border-0 bg-gradient-to-r from-[#d4a96a] to-[#b8874a] text-sm font-semibold text-white shadow-[0_4px_14px_rgba(155,108,43,0.28)] transition-transform hover:-translate-y-px cursor-pointer"
    >
      <Plus className="h-4 w-4" strokeWidth={2.5} />
      Tạo cuộc trò chuyện
    </button>

    <SidebarNav />

    <div className="mt-auto flex flex-col gap-4 pt-6">
      <SidebarUpgrade />
      <SidebarUser />
    </div>
  </aside>
);
