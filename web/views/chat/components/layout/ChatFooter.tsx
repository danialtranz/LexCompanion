import type { ReactNode } from "react";

interface ChatFooterProps {
  children: ReactNode;
}

export const ChatFooter = ({ children }: ChatFooterProps) => (
  <footer className="shrink-0 border-t border-[#ebe3d6] bg-[#faf7f2]/95 px-6 py-4 backdrop-blur-sm lg:px-8">
    <div className="mx-auto w-full max-w-3xl">{children}</div>
  </footer>
);
