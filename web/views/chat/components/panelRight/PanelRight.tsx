import type { ReactNode } from "react";

interface PanelRightProps {
  children: ReactNode;
}

export const PanelRight = ({ children }: PanelRightProps) => (
  <aside className="hidden min-h-screen w-full shrink-0 flex-col border-l border-[#ebe3d6] bg-white lg:flex">
    {children}
  </aside>
);
