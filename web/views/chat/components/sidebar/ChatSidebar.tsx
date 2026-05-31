import { SidebarBrand } from "./SidebarBrand";
import { SidebarNav } from "./SidebarNav";
import { SidebarUpgrade } from "./SidebarUpgrade";
import { SidebarUser } from "./SidebarUser";

export const ChatSidebar = () => (
  <aside className="hidden min-h-screen w-[186px] shrink-0 flex-col border-r border-[#eee4d7] bg-[rgba(255,254,251,0.82)] px-4 pb-[26px] pt-[42px] lg:flex">
    <SidebarBrand />
    <SidebarNav />
    <SidebarUpgrade />
    <SidebarUser />
  </aside>
);
