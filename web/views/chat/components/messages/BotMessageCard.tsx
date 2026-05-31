import Image from "next/image";
import type { BotMessage as BotMessageType } from "../../types";
import { SourceReferences } from "../sources/SourceReferences";

const LAWBOT_LOGO = "/images/icons/lawbot-logo.png";

interface BotMessageCardProps {
  message: BotMessageType;
}

export const BotMessageCard = ({ message }: BotMessageCardProps) => (
  <div className="mt-7">
    <div className="flex items-start gap-[18px]">
      <div className="grid h-[54px] w-[54px] shrink-0 place-items-center rounded-full border border-[#ead6b4] bg-[#fff5e3]">
        <Image
          src={LAWBOT_LOGO}
          alt="LawBot"
          width={28}
          height={28}
          className="h-7 w-7 object-contain"
        />
      </div>

      <div className="min-w-0 flex-1">
        <div className="w-full max-w-[720px] rounded-[14px] border border-[#eee4d7] bg-white/90 px-6 py-[22px] shadow-[0_18px_45px_rgba(84,59,28,0.09)]">
          <div className="text-[13px] font-bold text-[#9b6416]">LawBot</div>
          <p className="mt-2 text-sm leading-[1.85] text-[#29251f]">
            {message.intro}
          </p>
          <ol className="my-2 list-decimal space-y-1 pl-5 text-sm leading-[1.85] text-[#29251f]">
            {message.steps.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
          <p className="text-sm leading-[1.85] text-[#29251f]">
            {message.outro}{" "}
            <span className="float-right text-xs text-[#9e958b]">
              {message.time}
            </span>
          </p>
        </div>

        {message.sources.length > 0 && (
          <SourceReferences sources={message.sources} />
        )}
      </div>
    </div>
  </div>
);
