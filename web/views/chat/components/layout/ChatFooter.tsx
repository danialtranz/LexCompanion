import type { ReactNode } from "react";

interface ChatFooterProps {
  children: ReactNode;
  variant?: "default" | "live";
}

export const ChatFooter = ({
  children,
  variant = "default",
}: ChatFooterProps) => (
  <footer
    className={`relative z-20 shrink-0 border-t backdrop-blur-sm ${
      variant === "live"
        ? "border-[#ebe3d6] bg-white px-4 py-3"
        : "border-[#ebe3d6] bg-[#faf7f2]/95 px-6 py-4 lg:px-8"
    }`}
  >
    <div
      className={
        variant === "live" ? "w-full" : "mx-auto w-full max-w-3xl"
      }
    >
      {children}
    </div>
  </footer>
);
