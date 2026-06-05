import type { ReactNode } from "react";

interface PanelRightProps {
  children: ReactNode;
  /** Panel văn bản live — chiếm toàn bộ chiều cao, căn sát cạnh phải. */
  liveDocument?: boolean;
}

export const PanelRight = ({ children, liveDocument = false }: PanelRightProps) => (
  <aside
    className={`hidden min-h-screen min-w-0 w-full flex-col overflow-hidden border-l border-[#ebe3d6] lg:flex lg:flex-col ${
      liveDocument ? "bg-[#ece8e1]" : "bg-white"
    }`}
  >
    {children}
  </aside>
);
