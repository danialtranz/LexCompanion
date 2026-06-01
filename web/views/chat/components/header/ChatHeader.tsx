import { Bookmark, ChevronDown, Search } from "lucide-react";

export const ChatHeader = () => (
  <header className="flex h-[60px] shrink-0 items-center justify-between border-b border-[#ebe3d6] bg-[#faf7f2]/95 px-6 backdrop-blur-sm lg:px-8">
    <button
      type="button"
      className="flex items-center gap-1.5 border-0 bg-transparent p-0 text-[15px] font-semibold text-[#2c2620] cursor-default"
      aria-haspopup="listbox"
    >
      Danh sách các cuộc trò chuyện gần đây
      <ChevronDown className="h-4 w-4 text-[#8a8178]" strokeWidth={2} />
    </button>

    <div className="flex items-center gap-2">
      <button
        type="button"
        aria-label="Tìm kiếm"
        className="grid h-9 w-9 place-items-center rounded-full border border-[#ebe3d6] bg-white text-[#4a433c] shadow-sm transition-colors hover:border-[#dcc9a8] hover:text-[#9a6c2b] cursor-pointer"
      >
        <Search className="h-4 w-4" strokeWidth={2} />
      </button>
      <button
        type="button"
        aria-label="Đánh dấu"
        className="grid h-9 w-9 place-items-center rounded-full border border-[#ebe3d6] bg-white text-[#4a433c] shadow-sm transition-colors hover:border-[#dcc9a8] hover:text-[#9a6c2b] cursor-pointer"
      >
        <Bookmark className="h-4 w-4" strokeWidth={2} />
      </button>
    </div>
  </header>
);
