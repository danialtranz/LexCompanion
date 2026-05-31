import type { ReactNode } from "react";
import { ChatSidebar } from "../sidebar/ChatSidebar";

interface ChatLayoutProps {
  children: ReactNode;
}

export const ChatLayout = ({ children }: ChatLayoutProps) => (
  <main className="grid min-h-screen grid-cols-1 bg-[linear-gradient(90deg,rgba(255,255,255,0.88),rgba(255,255,255,0.96)),radial-gradient(circle_at_74%_14%,rgba(214,162,67,0.12),transparent_20%)] lg:grid-cols-[186px_1fr]">
    <ChatSidebar />
    {children}
  </main>
);
