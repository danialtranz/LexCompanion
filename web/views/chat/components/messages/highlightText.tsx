import { type ReactNode } from "react";

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

export function highlightText(text: string, keyword: string): ReactNode {
  const query = keyword.trim();
  if (!query) return text;

  const regex = new RegExp(`(${escapeRegExp(query)})`, "gi");
  const parts = text.split(regex);

  return parts.map((part, idx) => {
    if (part.toLowerCase() !== query.toLowerCase()) {
      return part;
    }
    return (
      <mark
        key={`hl-${idx}-${part}`}
        className="rounded bg-[#ffe5a6] px-0.5 text-inherit"
      >
        {part}
      </mark>
    );
  });
}
