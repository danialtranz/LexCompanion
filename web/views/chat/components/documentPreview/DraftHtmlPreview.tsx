"use client";

import styles from "./DraftHtmlPreview.module.css";

export type DraftHtmlPreviewProps = {
  html: string;
  className?: string;
  /** Bỏ khung bọc — dùng khi nội dung nằm trong trang giấy live layout. */
  bare?: boolean;
};

/**
 * Hiển thị HTML từ DOCX nháp (BE convert). Nội dung đã escape phía server.
 */
export const DraftHtmlPreview = ({
  html,
  className = "",
  bare = false,
}: DraftHtmlPreviewProps) => (
  <div
    className={`${bare ? styles.bare : styles.root} ${className}`}
    // eslint-disable-next-line react/no-danger
    dangerouslySetInnerHTML={{ __html: html }}
  />
);
