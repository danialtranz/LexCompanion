import { Diamond, Search } from "lucide-react";

export const ChatActions = () => (
  <div className="absolute right-8 top-[42px] z-10 flex gap-4 lg:right-16">
    <button
      type="button"
      aria-label="Tìm kiếm"
      className="grid h-[38px] w-[38px] place-items-center rounded-full border-0 bg-white text-[#2f2923] shadow-[0_10px_26px_rgba(80,56,31,0.08)] transition-transform hover:-translate-y-px cursor-pointer"
    >
      <Search className="h-4 w-4" strokeWidth={2} />
    </button>
    <button
      type="button"
      aria-label="Chia sẻ"
      className="grid h-[38px] w-[38px] place-items-center rounded-full border-0 bg-white text-[#2f2923] shadow-[0_10px_26px_rgba(80,56,31,0.08)] transition-transform hover:-translate-y-px cursor-pointer"
    >
      <Diamond className="h-4 w-4" strokeWidth={2} />
    </button>
  </div>
);
