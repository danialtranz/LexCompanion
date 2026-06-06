"use client";

import { useTranslation } from "react-i18next";
import styles from "./PlainTextDraftPreview.module.css";

export type PlainTextDraftPreviewProps = {
  text: string;
  placeholder?: string;
  bare?: boolean;
  className?: string;
};

/** Fallback read-only khi đang stream hoặc chưa có DOCX từ MinIO. */
export const PlainTextDraftPreview = ({
  text,
  placeholder,
  bare = false,
  className = "",
}: PlainTextDraftPreviewProps) => {
  const { t } = useTranslation();
  const resolvedPlaceholder = placeholder ?? t("chat.draft.noDraftContent");
  const trimmed = (text || "").trim();
  const shellClass = bare ? styles.bare : styles.root;

  if (!trimmed) {
    return (
      <div className={`${shellClass} ${className}`}>
        <p className={styles.placeholder}>{resolvedPlaceholder}</p>
      </div>
    );
  }

  return (
    <div className={`${shellClass} ${className}`}>
      <pre className={styles.text}>{text}</pre>
    </div>
  );
};
