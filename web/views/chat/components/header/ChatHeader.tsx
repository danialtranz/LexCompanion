"use client";

import { ChevronDown, Search } from "lucide-react";
import { useTranslation } from "react-i18next";
import { LanguageSwitcher } from "./LanguageSwitcher";

type ChatHeaderProps = {
  historyOpen?: boolean;
  onToggleHistory?: () => void;
  searchOpen?: boolean;
  searchValue?: string;
  onToggleSearch?: () => void;
  onSearchChange?: (value: string) => void;
};

export const ChatHeader = ({
  historyOpen = false,
  onToggleHistory,
  searchOpen = false,
  searchValue = "",
  onToggleSearch,
  onSearchChange,
}: ChatHeaderProps) => {
  const { t } = useTranslation();

  return (
    <header className="relative z-40 flex h-[60px] shrink-0 items-center justify-between overflow-visible border-b border-[#ebe3d6] bg-[#faf7f2]/95 px-6 backdrop-blur-sm lg:px-8">
      <button
        type="button"
        onClick={onToggleHistory}
        className="flex items-center gap-1.5 border-0 bg-transparent p-0 text-[15px] font-semibold text-[#2c2620] cursor-pointer"
        aria-haspopup="listbox"
        aria-expanded={historyOpen}
      >
        {t("chat.header.recentConversations")}
        <ChevronDown
          className={`h-4 w-4 text-[#8a8178] transition-transform ${historyOpen ? "rotate-180" : ""}`}
          strokeWidth={2}
        />
      </button>

      <div className="flex items-center gap-2">
        {searchOpen && (
          <input
            value={searchValue}
            onChange={(e) => onSearchChange?.(e.target.value)}
            placeholder={t("chat.header.searchPlaceholder")}
            className="h-9 w-64 rounded-full border border-[#dcc9a8] bg-white px-3 text-sm text-[#2c2620] outline-none placeholder:text-[#9b9389] focus:ring-2 focus:ring-[#f0dec2]"
          />
        )}
        <button
          type="button"
          onClick={onToggleSearch}
          aria-label={t("chat.header.search")}
          className={`grid h-9 w-9 place-items-center rounded-full border bg-white shadow-sm transition-colors cursor-pointer ${
            searchOpen
              ? "border-[#d4a96a] text-[#9a6c2b]"
              : "border-[#ebe3d6] text-[#4a433c] hover:border-[#dcc9a8] hover:text-[#9a6c2b]"
          }`}
        >
          <Search className="h-4 w-4" strokeWidth={2} />
        </button>
        <LanguageSwitcher />
      </div>
    </header>
  );
};
