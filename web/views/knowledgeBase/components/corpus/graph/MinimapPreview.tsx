import { NODE_COLOR } from "../constants";

export function MinimapPreview({
  imageUrl,
  isDark,
}: {
  imageUrl: string | null;
  isDark: boolean;
}) {
  return (
    <div
      className={`pointer-events-none absolute bottom-4 left-44 z-10 hidden h-[88px] w-[120px] overflow-hidden rounded-xl border shadow-md backdrop-blur-sm sm:block ${
        isDark
          ? "border-slate-700/80 bg-slate-900/80"
          : "border-white/80 bg-white/85"
      }`}
    >
      {imageUrl ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={imageUrl}
          alt="Minimap"
          className="h-full w-full object-cover opacity-90"
        />
      ) : (
        <div className="flex h-full items-center justify-center">
          <div className="flex flex-wrap gap-1 p-2">
            {[
              NODE_COLOR.topic,
              NODE_COLOR.subject,
              NODE_COLOR.article,
              NODE_COLOR.topic,
            ].map((color, i) => (
              <span
                key={i}
                className="h-2 w-2 rounded-full"
                style={{ backgroundColor: color }}
              />
            ))}
          </div>
        </div>
      )}
      <div className="absolute inset-3 rounded border border-emerald-400/50" />
    </div>
  );
}
