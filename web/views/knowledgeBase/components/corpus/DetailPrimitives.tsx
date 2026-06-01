import { Hash, type LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import type { NodeType } from "./types";

export function StatCard({
  label,
  value,
  tone,
}: {
  label: string;
  value: ReactNode;
  tone: "emerald" | "sky" | "violet";
}) {
  const tones = {
    emerald: "bg-emerald-50 text-emerald-900 border-emerald-100",
    sky: "bg-sky-50 text-sky-900 border-sky-100",
    violet: "bg-violet-50 text-violet-900 border-violet-100",
  };

  return (
    <div className={`rounded-xl border px-3 py-2.5 ${tones[tone]}`}>
      <p className="text-[10px] font-semibold uppercase tracking-wide opacity-70">
        {label}
      </p>
      <p className="mt-0.5 text-lg font-bold tabular-nums">{value ?? "—"}</p>
    </div>
  );
}

export function DetailRow({
  icon: Icon,
  label,
  value,
}: {
  icon: LucideIcon;
  label: string;
  value: ReactNode;
}) {
  if (value === null || value === undefined || value === "") return null;
  return (
    <div className="flex gap-3 border-b border-slate-100 py-3 last:border-0">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-slate-500">
        <Icon className="h-4 w-4" />
      </div>
      <div className="min-w-0 flex-1">
        <dt className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
          {label}
        </dt>
        <dd className="mt-0.5 break-words text-sm leading-relaxed text-slate-800">
          {value}
        </dd>
      </div>
    </div>
  );
}

export function NodeTypeBadge({ type }: { type: NodeType }) {
  const styles = {
    topic: "bg-emerald-100 text-emerald-800",
    subject: "bg-sky-100 text-sky-800",
    article: "bg-violet-100 text-violet-800",
  };
  const labels = { topic: "Topic", subject: "Subject", article: "Article" };

  return (
    <span
      className={`inline-flex items-center rounded-lg px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider ${styles[type]}`}
    >
      {labels[type]}
    </span>
  );
}
