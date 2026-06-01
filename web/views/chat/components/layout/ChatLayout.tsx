import type { ReactNode } from "react";
import { ChatSidebar } from "../sidebar/ChatSidebar";

interface ChatLayoutProps {
  children: ReactNode;
  panelRight?: ReactNode;
}

export const ChatLayout = ({ children, panelRight }: ChatLayoutProps) => (
  <main
    className={`grid min-h-screen grid-cols-1 bg-[#faf7f2] ${
      panelRight
        ? "lg:grid-cols-[240px_minmax(0,1fr)_400px]"
        : "lg:grid-cols-[240px_minmax(0,1fr)]"
    }`}
  >
    <ChatSidebar />
    {children}
    {panelRight}
  </main>
);
