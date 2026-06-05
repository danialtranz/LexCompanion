"use client";

import { useEffect, useRef, useState } from "react";
import styles from "./DocxBlobPreview.module.css";

export type DocxBlobPreviewProps = {
  blob: Blob | null;
  className?: string;
  /** Bỏ khung bọc — dùng khi nội dung nằm trong trang giấy live layout. */
  bare?: boolean;
};

/** Giữ layout DOCX gần nhất có thể — font, căn lề, tab, ngắt trang. */
const DOCX_PREVIEW_OPTIONS = {
  className: "docx",
  inWrapper: true,
  ignoreWidth: false,
  ignoreHeight: false,
  ignoreFonts: false,
  breakPages: true,
  ignoreLastRenderedPageBreak: false,
  experimental: true,
  useBase64URL: true,
  renderHeaders: true,
  renderFooters: true,
  renderFootnotes: true,
  renderEndnotes: true,
  renderAltChunks: true,
} as const;

export const DocxBlobPreview = ({
  blob,
  className = "",
  bare = false,
}: DocxBlobPreviewProps) => {
  const bodyRef = useRef<HTMLDivElement>(null);
  const styleRef = useRef<HTMLDivElement>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const bodyEl = bodyRef.current;
    const styleEl = styleRef.current;
    if (!blob?.size || !bodyEl || !styleEl) {
      if (bodyEl) bodyEl.innerHTML = "";
      if (styleEl) styleEl.innerHTML = "";
      setLoading(false);
      setError(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);
    bodyEl.innerHTML = "";
    styleEl.innerHTML = "";

    void (async () => {
      try {
        const { renderAsync } = await import("docx-preview");
        const arrayBuffer = await blob.arrayBuffer();
        if (cancelled) return;
        await renderAsync(arrayBuffer, bodyEl, styleEl, DOCX_PREVIEW_OPTIONS);
        if (!cancelled) setLoading(false);
      } catch (e) {
        if (!cancelled) {
          setError(
            e instanceof Error ? e.message : "Không đọc được file DOCX",
          );
          setLoading(false);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [blob]);

  const shellClass = bare ? styles.bare : styles.root;

  return (
    <div className={`${shellClass} ${className}`}>
      <div ref={styleRef} className={styles.styleHost} aria-hidden />
      <div ref={bodyRef} className={styles.bodyHost} />
      {loading ? (
        <p className={styles.status}>Đang render bản nháp…</p>
      ) : null}
      {error ? <p className={styles.error}>{error}</p> : null}
    </div>
  );
};
