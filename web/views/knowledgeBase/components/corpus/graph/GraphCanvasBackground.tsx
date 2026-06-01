import { PARTICLE_POSITIONS } from "../constants";

export function GraphCanvasBackground({ isDark }: { isDark: boolean }) {
  return (
    <div
      className="pointer-events-none absolute inset-0 overflow-hidden"
      aria-hidden
    >
      <div
        className={`absolute inset-0 ${
          isDark
            ? "bg-[radial-gradient(circle_at_center,#1e293b_0%,#0f172a_55%,#020617_100%)]"
            : "bg-[radial-gradient(circle_at_center,#ffffff_0%,#eef2f7_50%,#e2e8f0_100%)]"
        }`}
      />
      {[140, 220, 300, 380, 460].map((radius) => (
        <div
          key={radius}
          className={`absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full border border-dashed ${
            isDark ? "border-slate-600/30" : "border-slate-300/45"
          }`}
          style={{ width: radius * 2, height: radius * 2 }}
        />
      ))}
      {PARTICLE_POSITIONS.map(([left, top], index) => (
        <div
          key={index}
          className={`absolute h-1 w-1 rounded-full ${
            isDark ? "bg-slate-500/40" : "bg-slate-400/35"
          }`}
          style={{ left: `${left}%`, top: `${top}%` }}
        />
      ))}
    </div>
  );
}
