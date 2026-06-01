import type { ReactNode } from "react";

export function GraphControlButton({
  title,
  onClick,
  children,
  active,
}: {
  title: string;
  onClick: () => void;
  children: ReactNode;
  active?: boolean;
}) {
  return (
    <button
      type="button"
      title={title}
      aria-label={title}
      onClick={onClick}
      className={`flex h-9 w-9 items-center justify-center rounded-xl border shadow-sm transition ${
        active
          ? "border-emerald-200 bg-emerald-50 text-emerald-700"
          : "border-white/80 bg-white/90 text-slate-600 hover:bg-white hover:text-slate-900"
      }`}
    >
      {children}
    </button>
  );
}
