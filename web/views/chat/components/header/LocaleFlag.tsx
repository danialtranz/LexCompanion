"use client";

import { useId } from "react";
import type { AppLocale } from "@/locale/i18n";

type LocaleFlagProps = {
  locale: AppLocale;
  className?: string;
};

/** Cờ Việt Nam — tỷ lệ 3:2, sao vàng 5 cánh đường kính 2/5 chiều ngang. */
function VietnamFlag() {
  return (
    <svg
      viewBox="0 0 30 20"
      className="h-full w-full"
      preserveAspectRatio="xMidYMid slice"
      aria-hidden
    >
      <rect width="30" height="20" fill="#DA251D" />
      <polygon
        fill="#FFCD00"
        transform="translate(15 10)"
        points="0,-6 1.76,-1.85 5.85,-1.85 2.29,0.95 3.54,6.2 0,2.6 -3.54,6.2 -2.29,0.95 -5.85,-1.85 -1.76,-1.85"
      />
    </svg>
  );
}

function UkFlag({ clipId }: { clipId: string }) {
  const tId = `${clipId}-t`;

  return (
    <svg
      viewBox="0 0 60 30"
      className="h-full w-full"
      preserveAspectRatio="xMidYMid slice"
      aria-hidden
    >
      <clipPath id={clipId}>
        <path d="M0,0 v30 h60 v-30 z" />
      </clipPath>
      <clipPath id={tId}>
        <path d="M30,15 h30 v15 z v15 h-30 z h-30 v-15 z v-15 h30 z" />
      </clipPath>
      <g clipPath={`url(#${clipId})`}>
        <path d="M0,0 v30 h60 v-30 z" fill="#012169" />
        <path d="M0,0 L60,30 M60,0 L0,30" stroke="#fff" strokeWidth="6" />
        <path
          d="M0,0 L60,30 M60,0 L0,30"
          clipPath={`url(#${tId})`}
          stroke="#C8102E"
          strokeWidth="4"
        />
        <path d="M30,0 v30 M0,15 h60" stroke="#fff" strokeWidth="10" />
        <path d="M30,0 v30 M0,15 h60" stroke="#C8102E" strokeWidth="6" />
      </g>
    </svg>
  );
}

export const LocaleFlag = ({
  locale,
  className = "h-4 w-4",
}: LocaleFlagProps) => {
  const clipId = useId().replace(/:/g, "");

  return (
    <span
      className={`inline-flex shrink-0 overflow-hidden rounded-full ring-1 ring-[#ebe3d6] ${className}`}
      aria-hidden
    >
      {locale === "vi" ? (
        <VietnamFlag />
      ) : (
        <UkFlag clipId={`uk-${clipId}`} />
      )}
    </span>
  );
};
