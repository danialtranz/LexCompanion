import type { UserMessage as UserMessageType } from "../../types";

interface UserMessageCardProps {
  message: UserMessageType;
}

export const UserMessageCard = ({ message }: UserMessageCardProps) => (
  <div className="mt-11 w-full max-w-[720px] rounded-[14px] border border-[#eee4d7] bg-white/90 px-6 py-[22px] shadow-[0_18px_45px_rgba(84,59,28,0.09)]">
    <div className="text-[13px] font-bold text-[#201914]">
      Bạn{" "}
      <span className="float-right text-xs font-normal text-[#9e958b]">
        {message.time}
      </span>
    </div>
    <p className="clear-both mt-2 text-sm leading-[1.85] text-[#29251f]">
      {message.content}
    </p>
  </div>
);
