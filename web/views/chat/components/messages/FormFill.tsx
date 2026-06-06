"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Loader2, SendHorizontal } from "lucide-react";
import { useTranslation } from "react-i18next";
import type { MessageFormFill } from "../../types";
import {
  buildFieldValuesSummary,
  getFieldsToFill,
} from "../../utils/formFillHitl";

export type FormFillProps = {
  formFill: MessageFormFill;
  loading?: boolean;
  disabled?: boolean;
  onSubmit: (fieldValues: Record<string, string>) => void;
  onReject?: () => void;
};

function isMultilineField(fieldId: string, label: string): boolean {
  const key = `${fieldId} ${label}`.toLowerCase();
  return (
    key.includes("yeu_cau") ||
    key.includes("yêu cầu") ||
    key.includes("danh_muc") ||
    key.includes("danh mục") ||
    key.includes("thong_tin") ||
    key.includes("nội dung")
  );
}

export const FormFill = ({
  formFill,
  loading = false,
  disabled = false,
  onSubmit,
  onReject,
}: FormFillProps) => {
  const { t } = useTranslation();
  const fields = useMemo(() => getFieldsToFill(formFill), [formFill]);
  const { filled_values = {}, clarification_questions = [], actions } =
    formFill.hitl;

  const initialValues = useMemo(() => {
    const next: Record<string, string> = { ...filled_values };
    for (const f of fields) {
      if (!next[f.id] && f.value) {
        next[f.id] = f.value;
      }
    }
    return next;
  }, [fields, filled_values]);

  const [values, setValues] = useState<Record<string, string>>(initialValues);

  useEffect(() => {
    setValues(initialValues);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- reset khi HITL interrupt mới
  }, [formFill.hitl.interrupt_id]);

  const setField = useCallback((id: string, value: string) => {
    setValues((prev) => ({ ...prev, [id]: value }));
  }, []);

  const missingRequired = fields.filter(
    (f) => f.required && !(values[f.id] || "").trim(),
  );

  const canSubmit = !disabled && !loading && missingRequired.length === 0;

  const handleSubmit = () => {
    if (!canSubmit) return;
    const payload: Record<string, string> = {};
    for (const f of fields) {
      const v = (values[f.id] || "").trim();
      if (v) payload[f.id] = v;
    }
    onSubmit(payload);
  };

  const chunkHint =
    formFill.hitl.chunk_total != null && formFill.hitl.chunk_index != null
      ? t("chat.formFill.chunkHint", {
          current: formFill.hitl.chunk_index + 1,
          total: formFill.hitl.chunk_total,
        })
      : "";

  if (fields.length === 0) {
    return (
      <p className="m-0 text-sm text-[#8a8178]">
        {t("chat.formFill.noFields")}
      </p>
    );
  }

  return (
    <div className="mt-4 border-t border-[#f0e6d8] pt-4">
      <p className="m-0 text-xs font-semibold uppercase tracking-wide text-[#9a6c2b]">
        {chunkHint}
        {t("chat.formFill.title")}
      </p>

      {clarification_questions.length > 0 && (
        <ul className="mt-2.5 mb-0 list-none space-y-1.5 pl-0">
          {clarification_questions.map((q) => (
            <li
              key={q}
              className="text-sm leading-relaxed text-[#5c5349] before:mr-2 before:text-[#c9a06a] before:content-['•']"
            >
              {q}
            </li>
          ))}
        </ul>
      )}

      <div className="mt-4 space-y-3">
        {fields.map((field) => {
          const multiline = isMultilineField(field.id, field.label);
          const inputId = `form-fill-${field.id}`;
          return (
            <div key={field.id}>
              <label
                htmlFor={inputId}
                className="mb-1 block text-xs font-medium text-[#5c5349]"
              >
                {field.label}
                {field.required ? (
                  <span className="text-[#b54545]" aria-hidden>
                    {" "}
                    *
                  </span>
                ) : (
                  <span className="font-normal text-[#a89f96]">
                    {" "}
                    {t("chat.formFill.optional")}
                  </span>
                )}
              </label>
              {multiline ? (
                <textarea
                  id={inputId}
                  rows={3}
                  disabled={disabled || loading}
                  value={values[field.id] ?? ""}
                  onChange={(e) => setField(field.id, e.target.value)}
                  placeholder={field.anchor_text?.slice(0, 80)}
                  className="w-full resize-y rounded-lg border border-[#ebe3d6] bg-[#fffdf9] px-3 py-2 text-sm text-[#2c2620] outline-none transition-colors placeholder:text-[#c4b8a8] focus:border-[#c9a06a] disabled:cursor-not-allowed disabled:opacity-60"
                />
              ) : (
                <input
                  id={inputId}
                  type="text"
                  disabled={disabled || loading}
                  value={values[field.id] ?? ""}
                  onChange={(e) => setField(field.id, e.target.value)}
                  placeholder={field.anchor_text?.slice(0, 60)}
                  className="h-10 w-full rounded-lg border border-[#ebe3d6] bg-[#fffdf9] px-3 text-sm text-[#2c2620] outline-none transition-colors placeholder:text-[#c4b8a8] focus:border-[#c9a06a] disabled:cursor-not-allowed disabled:opacity-60"
                />
              )}
            </div>
          );
        })}
      </div>

      {missingRequired.length > 0 && (
        <p className="mt-2 m-0 text-xs text-[#b54545]">
          {t("chat.formFill.missingRequired", {
            count: missingRequired.length,
          })}
        </p>
      )}

      <div className="mt-4 flex flex-wrap items-center justify-end gap-2">
        {actions.includes("reject") && onReject && (
          <button
            type="button"
            disabled={disabled || loading}
            onClick={onReject}
            className="cursor-pointer rounded-lg border border-[#ebe3d6] bg-white px-3 py-1.5 text-xs font-medium text-[#8a8178] transition-colors hover:bg-[#faf5ec] disabled:cursor-not-allowed disabled:opacity-50"
          >
            {t("chat.formFill.cancel")}
          </button>
        )}
        <button
          type="button"
          disabled={!canSubmit}
          onClick={handleSubmit}
          title={buildFieldValuesSummary(fields, values)}
          className="inline-flex cursor-pointer items-center gap-1.5 rounded-lg border-0 bg-gradient-to-br from-[#d4a96a] to-[#9a6c2b] px-4 py-2 text-xs font-semibold text-white shadow-[0_2px_8px_rgba(155,108,43,0.25)] transition-transform hover:-translate-y-px disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" strokeWidth={2.5} />
          ) : (
            <SendHorizontal className="h-3.5 w-3.5" strokeWidth={2.5} />
          )}
          {t("chat.formFill.submit")}
        </button>
      </div>
    </div>
  );
};
