import type { ReactNode } from "react";

interface ChatMainProps {
  children: ReactNode;
  footer?: ReactNode;
}

export const ChatMain = ({ children, footer }: ChatMainProps) => (
  <section className="flex min-h-screen min-w-0 flex-col bg-[#faf7f2]">
    {children}
    {footer}
  </section>
);
