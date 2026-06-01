import Image from "next/image";
import { Loader2 } from "lucide-react";

const LAWBOT_LOGO = "/images/icons/lawbot-logo.png";

export const ChatLoadingIndicator = () => (
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
    <div className="flex items-center gap-2.5 rounded-2xl border border-[#ebe3d6] bg-white px-5 py-4 text-sm text-[#8a8178] shadow-sm">
      <Loader2 className="h-4 w-4 animate-spin text-[#9a6c2b]" />
      Đang tra cứu và tổng hợp câu trả lời…
    </div>
  </div>
);
