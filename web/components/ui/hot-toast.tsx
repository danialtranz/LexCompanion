import * as React from "react";
import type { TFunction } from "i18next";
import { Toaster, toast as hotToast } from "react-hot-toast";
import { useTranslation } from "react-i18next";

export type I18nText =
  | string
  | {
      key: string;
      values?: Record<string, unknown>;
      defaultValue?: string;
    };

function resolveI18nText(t: TFunction, input?: I18nText): string | undefined {
  if (!input) return undefined;
  if (typeof input === "string") return input;
  return t(input.key, {
    ...(input.values ?? {}),
    defaultValue: input.defaultValue,
  });
}

export type HotToastOptions = {
  /** override duration for this toast */
  duration?: number;
};

/**
 * Hook dùng để show react-hot-toast với hỗ trợ đa ngôn ngữ.
 *
 * Usage:
 * const { success, error } = useHotToast();
 * success({ key: "message.saveSuccess" })
 */
export function useHotToast() {
  const { t } = useTranslation();

  const success = React.useCallback(
    (text: I18nText, options?: HotToastOptions) => {
      hotToast.success(resolveI18nText(t, text) ?? "", {
        duration: options?.duration,
      });
    },
    [t]
  );

  const error = React.useCallback(
    (text: I18nText, options?: HotToastOptions) => {
      hotToast.error(resolveI18nText(t, text) ?? "", {
        duration: options?.duration,
      });
    },
    [t]
  );

  const info = React.useCallback(
    (text: I18nText, options?: HotToastOptions) => {
      hotToast(resolveI18nText(t, text) ?? "", { duration: options?.duration });
    },
    [t]
  );

  return { success, error, info };
}

/**
 * Component mount 1 lần ở app root để render react-hot-toast UI.
 */
export function HotToaster() {
  return (
    <Toaster
      position="top-center"
      containerStyle={{
        top: "35px",
      }}
      toastOptions={{
        duration: 3000,
        style: {
          background:
            "linear-gradient(135deg, rgba(255, 255, 255, 0.95), rgba(248, 250, 252, 0.92))",
          color: "#1e293b",
          border: "1px solid rgba(34, 211, 238, 0.35)",
          backdropFilter: "blur(8px)",
          boxShadow: "0 16px 48px rgba(0,0,0,0.6)",
          borderRadius: "16px",
          fontWeight: "500",
          padding: "10px 15px",
        },
      }}
    />
  );
}
