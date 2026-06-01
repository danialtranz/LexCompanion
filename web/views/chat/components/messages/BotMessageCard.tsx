import Image from "next/image";
import type { BotMessage as BotMessageType, ChatCitation } from "../../types";
import { BotMessageActions } from "./BotMessageActions";
import { BotMessageContent } from "./BotMessageContent";
import { MessageCitationList } from "./MessageCitationList";

const LAWBOT_LOGO = "/images/icons/lawbot-logo.png";

interface BotMessageCardProps {
  message: BotMessageType;
  selectedCitationId?: string;
  onSelectCitation?: (citation: ChatCitation) => void;
}

export const BotMessageCard = ({
  message,
  selectedCitationId,
  onSelectCitation,
}: BotMessageCardProps) => (
  <div className="flex items-start gap-3">
    <div className="grid h-10 w-10 shrink-0 place-items-center rounded-full border border-[#e8dcc8] bg-white shadow-sm">
      <Image
        src={LAWBOT_LOGO}
        alt="LawBot"
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
            LawBot
          </span>
          <span className="shrink-0 text-xs text-[#8a8178]">{message.time}</span>
        </div>

        <div className="mt-2.5">
          <BotMessageContent
            content={message.content}
            citations={message.citations}
            selectedCitationId={selectedCitationId}
            onSelectCitation={onSelectCitation}
            error={message.error}
          />
        </div>

        {!message.error && <BotMessageActions />}
      </div>

      {!message.error && message.citations.length > 0 && onSelectCitation && (
        <MessageCitationList
          citations={message.citations}
          selectedCitationId={selectedCitationId}
          onSelectCitation={onSelectCitation}
        />
      )}
    </div>
  </div>
);
