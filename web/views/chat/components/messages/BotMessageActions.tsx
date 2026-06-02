import { Copy, ThumbsDown, ThumbsUp } from "lucide-react";
import { useRef, useState } from "react";

type BotMessageActionsProps = {
  content: string;
};

type FeedbackState = "like" | "dislike" | null;

function triggerShake(element: Element | null) {
  if (!element || typeof element.animate !== "function") return;
  element.animate(
    [
      { transform: "translateX(0)" },
      { transform: "translateX(-2px) rotate(-10deg)" },
      { transform: "translateX(2px) rotate(10deg)" },
      { transform: "translateX(-2px) rotate(-8deg)" },
      { transform: "translateX(2px) rotate(8deg)" },
      { transform: "translateX(0)" },
    ],
    { duration: 300, easing: "ease-in-out" },
  );
}

async function copyToClipboard(text: string) {
  if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }
  if (typeof document === "undefined") return;

  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "absolute";
  textarea.style.left = "-9999px";
  document.body.appendChild(textarea);
  textarea.select();
  document.execCommand("copy");
  document.body.removeChild(textarea);
}

export const BotMessageActions = ({ content }: BotMessageActionsProps) => {
  const [feedback, setFeedback] = useState<FeedbackState>(null);
  const [copied, setCopied] = useState(false);
  const likeIconRef = useRef<SVGSVGElement | null>(null);
  const dislikeIconRef = useRef<SVGSVGElement | null>(null);

  const handleCopy = async () => {
    try {
      await copyToClipboard(content);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1200);
    } catch {
      setCopied(false);
    }
  };

  const handleLike = () => {
    setFeedback("like");
    triggerShake(likeIconRef.current);
  };

  const handleDislike = () => {
    setFeedback("dislike");
    triggerShake(dislikeIconRef.current);
  };

  return (
    <div className="mt-4 flex items-center gap-1 border-t border-[#f3ece2] pt-3">
      <button
        type="button"
        aria-label="Sao chép"
        title={copied ? "Đã sao chép" : "Sao chép"}
        onClick={handleCopy}
        className={`grid h-8 w-8 place-items-center rounded-lg border-0 bg-transparent transition-colors cursor-pointer ${
          copied
            ? "text-[#9a6c2b] bg-[#faf5ec]"
            : "text-[#9a9289] hover:bg-[#faf5ec] hover:text-[#9a6c2b]"
        }`}
      >
        <Copy className="h-4 w-4" strokeWidth={2} />
      </button>
      <button
        type="button"
        aria-label="Hữu ích"
        onClick={handleLike}
        className={`grid h-8 w-8 place-items-center rounded-lg border-0 bg-transparent transition-colors cursor-pointer ${
          feedback === "like"
            ? "text-[#9a6c2b] bg-[#faf5ec]"
            : "text-[#9a9289] hover:bg-[#faf5ec] hover:text-[#9a6c2b]"
        }`}
      >
        <ThumbsUp ref={likeIconRef} className="h-4 w-4" strokeWidth={2} />
      </button>
      <button
        type="button"
        aria-label="Không hữu ích"
        onClick={handleDislike}
        className={`grid h-8 w-8 place-items-center rounded-lg border-0 bg-transparent transition-colors cursor-pointer ${
          feedback === "dislike"
            ? "text-[#9a6c2b] bg-[#faf5ec]"
            : "text-[#9a9289] hover:bg-[#faf5ec] hover:text-[#9a6c2b]"
        }`}
      >
        <ThumbsDown ref={dislikeIconRef} className="h-4 w-4" strokeWidth={2} />
      </button>
      <div className="ml-2 h-8">
        {copied && (
          <div
            role="status"
            aria-live="polite"
            className="inline-flex h-8 items-center rounded-lg border border-[#e2c4a0] bg-[#fff7ea] px-2.5 text-xs font-medium text-[#9a6c2b]"
          >
            Đã copy vào clipboard
          </div>
        )}
      </div>
    </div>
  );
};
