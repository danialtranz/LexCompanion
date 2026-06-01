import { type FormEvent, type KeyboardEvent } from "react";
import { Loader2, Paperclip, SendHorizontal } from "lucide-react";

interface ChatInputBoxProps {
  value: string;
  onChange: (value: string) => void;
  onSend?: () => void;
  loading?: boolean;
  disabled?: boolean;
}

export const ChatInputBox = ({
  value,
  onChange,
  onSend,
  loading = false,
  disabled = false,
}: ChatInputBoxProps) => {
  const isDisabled = disabled || loading;

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (isDisabled || !value.trim()) return;
    onSend?.();
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (isDisabled || !value.trim()) return;
      onSend?.();
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="flex h-14 items-center gap-2 rounded-2xl border border-[#ebe3d6] bg-white px-4 shadow-[0_4px_20px_rgba(84,59,28,0.06)]"
    >
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={handleKeyDown}
        disabled={isDisabled}
        placeholder="Nhập câu hỏi của bạn về pháp luật..."
        className="min-w-0 flex-1 border-0 bg-transparent text-sm text-[#2c2620] outline-none placeholder:text-[#a89f96] disabled:cursor-not-allowed disabled:opacity-60"
      />
      <button
        type="button"
        aria-label="Đính kèm tệp"
        className="grid h-9 w-9 shrink-0 place-items-center rounded-lg border-0 bg-transparent text-[#8a8178] transition-colors hover:bg-[#faf5ec] hover:text-[#9a6c2b] cursor-pointer"
      >
        <Paperclip className="h-[18px] w-[18px]" strokeWidth={2} />
      </button>
      <button
        type="submit"
        disabled={isDisabled || !value.trim()}
        aria-label="Gửi tin nhắn"
        className="grid h-10 w-10 shrink-0 place-items-center rounded-xl border-0 bg-gradient-to-br from-[#d4a96a] to-[#9a6c2b] text-white shadow-[0_4px_12px_rgba(155,108,43,0.3)] transition-transform hover:-translate-y-px cursor-pointer disabled:cursor-not-allowed disabled:opacity-50"
      >
        {loading ? (
          <Loader2 className="h-[18px] w-[18px] animate-spin" strokeWidth={2.5} />
        ) : (
          <SendHorizontal className="h-[18px] w-[18px]" strokeWidth={2.5} />
        )}
      </button>
    </form>
  );
};
