import type { ReactNode } from "react";

interface ChatMainProps {
  children: ReactNode;
}

export const ChatMain = ({ children }: ChatMainProps) => (
  <section className="relative min-h-screen overflow-hidden px-5 pb-28 pt-12 sm:px-8 lg:px-16 lg:pt-14">
    <div
      aria-hidden
      className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_78%_16%,rgba(217,168,76,0.16),transparent_16%),linear-gradient(180deg,rgba(255,255,255,0.42),transparent_38%)]"
    />
    <div className="relative z-[1]">{children}</div>
  </section>
);
