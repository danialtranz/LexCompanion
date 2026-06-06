"use client";

import Image from "next/image";
import { useTranslation } from "react-i18next";
import type { BotMessage as BotMessageType, ChatCitation } from "../../types";
import { BotMessageActions } from "./BotMessageActions";
import { BotMessageContent } from "./BotMessageContent";
import { FormFill } from "./FormFill";
import { MessageCitationList } from "./MessageCitationList";

const LAWBOT_LOGO = "/images/icons/lex-companion-logo.png";

interface BotMessageCardProps {
  message: BotMessageType;
  selectedCitationId?: string;
  onSelectCitation?: (citation: ChatCitation) => void;
  searchKeyword?: string;
  formFillActive?: boolean;
  formFillLoading?: boolean;
  onFormFillSubmit?: (
    messageId: string,
    fieldValues: Record<string, string>,
  ) => void;
  onFormFillReject?: (messageId: string) => void;
  variant?: "default" | "live";
}

export const BotMessageCard = ({
  message,
  selectedCitationId,
  onSelectCitation,
  searchKeyword = "",
  formFillActive = false,
  formFillLoading = false,
  onFormFillSubmit,
  onFormFillReject,
  variant = "default",
}: BotMessageCardProps) => {
  const { t } = useTranslation();
  const showFormFill =
    Boolean(message.formFill) &&
    !message.error &&
    formFillActive &&
    !message.formFill?.submitted;

  if (variant === "live") {
    return (
      <div className="flex flex-col gap-1">
        <div className="flex items-center gap-2 px-0.5">
          <div className="grid h-7 w-7 shrink-0 place-items-center rounded-full border border-[#b8e0c8] bg-[#edf8f1]">
            <Image
              src={LAWBOT_LOGO}
              alt={t("common.lawBot")}
              width={18}
              height={18}
              className="h-[18px] w-[18px] object-contain"
            />
          </div>
          <span
            className={`text-xs font-semibold ${message.error ? "text-[#b54545]" : "text-[#2d7a4a]"}`}
          >
            {t("chat.messages.aiLegal")}
          </span>
          <span className="ml-auto shrink-0 text-[10px] text-[#8a8178]">
            {message.time}
          </span>
        </div>
        <div
          className={`rounded-xl border px-3.5 py-3 ${
            message.error
              ? "border-[#f0d0d0] bg-[#fff8f8]"
              : "border-[#ebe3d6] bg-white"
          }`}
        >
          <BotMessageContent
            content={message.content}
            citations={message.citations}
            selectedCitationId={selectedCitationId}
            onSelectCitation={onSelectCitation}
            searchKeyword={searchKeyword}
            error={message.error}
          />
          {showFormFill && message.formFill && onFormFillSubmit && (
            <FormFill
              formFill={message.formFill}
              loading={formFillLoading}
              onSubmit={(fieldValues) =>
                onFormFillSubmit(message.id, fieldValues)
              }
              onReject={
                onFormFillReject
                  ? () => onFormFillReject(message.id)
                  : undefined
              }
            />
          )}
          {message.formFill?.submitted && (
            <p className="mt-2 mb-0 text-xs text-[#8a8178]">
              {t("chat.messages.formFillSubmitted")}
            </p>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-3">
      <div className="grid h-10 w-10 shrink-0 place-items-center rounded-full border border-[#e8dcc8] bg-white shadow-sm">
        <Image
          src={LAWBOT_LOGO}
          alt={t("common.lawBot")}
          width={24}
          height={24}
          className="h-6 w-6 object-contain"
        />
      </div>

      <div className="min-w-0 flex-1">
        <div
          className={`rounded-2xl border px-5 py-4 shadow-sm ${
            message.error
              ? "border-[#f0d0d0] bg-[#fff8f8]"
              : "border-[#ebe3d6] bg-white"
          }`}
        >
          <div className="flex items-center justify-between gap-3">
            <span
              className={`text-[13px] font-bold ${message.error ? "text-[#b54545]" : "text-[#9a6c2b]"}`}
            >
              {t("common.lawBot")}
            </span>
            <span className="shrink-0 text-xs text-[#8a8178]">
              {message.time}
            </span>
          </div>

          <div className="mt-2.5">
            <BotMessageContent
              content={message.content}
              citations={message.citations}
              selectedCitationId={selectedCitationId}
              onSelectCitation={onSelectCitation}
              searchKeyword={searchKeyword}
              error={message.error}
            />
          </div>

          {!message.error && !showFormFill && (
            <BotMessageActions content={message.content} />
          )}

          {showFormFill && message.formFill && onFormFillSubmit && (
            <FormFill
              formFill={message.formFill}
              loading={formFillLoading}
              onSubmit={(fieldValues) =>
                onFormFillSubmit(message.id, fieldValues)
              }
              onReject={
                onFormFillReject
                  ? () => onFormFillReject(message.id)
                  : undefined
              }
            />
          )}

          {message.formFill?.submitted && (
            <p className="mt-3 mb-0 border-t border-[#f0e6d8] pt-3 text-xs text-[#8a8178]">
              {t("chat.messages.formFillSubmitted")}
            </p>
          )}
        </div>

        {!message.error && message.citations.length > 0 && onSelectCitation && (
          <MessageCitationList
            citations={message.citations}
            selectedCitationId={selectedCitationId}
            onSelectCitation={onSelectCitation}
            searchKeyword={searchKeyword}
          />
        )}
      </div>
    </div>
  );
};
